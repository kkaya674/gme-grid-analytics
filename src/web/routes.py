from flask import Blueprint, render_template, jsonify, request, send_file
import os
import io
import pandas as pd
from datetime import date, datetime, timedelta
from gme_api.client import GMEClient
from services.forecasting import train_and_predict
import logging

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

def parse_gme_response(result, market_type):
    if not result:
        return []
    
    if isinstance(result, list):
        parsed_data = []
        
        if market_type == 'electricity':
            for item in result:
                if isinstance(item, dict):
                    zone = item.get('Zone', item.get('Zona', ''))
                    flow_date = item.get('FlowDate', item.get('date', ''))
                    hour = item.get('Hour', item.get('hour', item.get('interval', 1)))
                    period = item.get('Period', '')
                    price = item.get('Price', item.get('price', 0))
                    
                    volumes_purchased = item.get('VolumesPurchased', item.get('Purchased', 0))
                    volumes_sold = item.get('VolumesSold', item.get('Sold', 0))
                    
                    avg_purchase_price = item.get('AveragePurchasingPrice', 0)
                    avg_selling_price = item.get('AverageSellingPrice', 0)
                    min_purchase_price = item.get('MinimumPurchasingPrice', 0)
                    max_selling_price = item.get('MaximumSellingPrice', 0)
                    
                    if flow_date and isinstance(flow_date, int):
                        flow_date = str(flow_date)
                        if len(flow_date) == 8:
                            flow_date = f"{flow_date[0:4]}-{flow_date[4:6]}-{flow_date[6:8]}"
                    
                    display_price = price
                    if not price and avg_purchase_price:
                        display_price = avg_purchase_price
                    elif not price and avg_selling_price:
                        display_price = avg_selling_price
                    elif not price and min_purchase_price:
                        display_price = min_purchase_price
                    elif not price and max_selling_price:
                        display_price = max_selling_price
                    
                    total_volume = 0
                    if volumes_purchased:
                        total_volume = volumes_purchased
                    if volumes_sold and volumes_sold > total_volume:
                        total_volume = volumes_sold
                    
                    if display_price or total_volume:
                        try:
                            price_val = float(display_price) if display_price and display_price != 'null' and display_price != '' else 0
                            volume_val = float(total_volume) if total_volume and total_volume != 'null' and total_volume != '' else 0
                            
                            normalized_item = {
                                'date': flow_date if flow_date else item.get('Date', ''),
                                'interval': int(hour) if hour else 1,
                                'period': period,
                                'price': price_val,
                                'volume': volume_val,
                                'zone': zone if zone else 'National'
                            }
                            parsed_data.append(normalized_item)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Skipping item due to conversion error: {e}, item: {item}")
                            continue
        
        elif market_type == 'gas':
            for item in result:
                if isinstance(item, dict):
                    flow_date = item.get('FlowDate', item.get('date', ''))
                    product = item.get('Product', '')
                    
                    if flow_date and isinstance(flow_date, int):
                        flow_date = str(flow_date)
                        if len(flow_date) == 8:
                            flow_date = f"{flow_date[0:4]}-{flow_date[4:6]}-{flow_date[6:8]}"
                    try:
                        price_val = float(avg_price) if avg_price and avg_price != 'null' and avg_price != '' else 0
                        volume_val = float(mwh_volumes) if mwh_volumes and mwh_volumes != 'null' and mwh_volumes != '' else (float(mw_volumes) if mw_volumes and mw_volumes != 'null' and mw_volumes != '' else 0)
                        
                        normalized_item = {
                            'date': flow_date if flow_date else item.get('Date', ''),
                            'product': product,
                            'price': price_val,
                            'volume': volume_val
                        }
                        parsed_data.append(normalized_item)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping gas item due to conversion error: {e}")
                        continue
                    normalized_item = {
                        'date': flow_date if flow_date else item.get('Date', ''),
                        'product': product,
                        'price': float(avg_price) if avg_price else 0,
                        'volume': float(mwh_volumes) if mwh_volumes else float(mw_volumes) if mw_volumes else 0
                    }
                    parsed_data.append(normalized_item)
        
        elif market_type == 'environmental':
            for item in result:
                if isinstance(item, dict):
                    date_val = item.get('Date', item.get('FlowDate', ''))
                    type_val = item.get('Type', '')
                    ref_price = item.get('ReferencePrice', item.get('WeightedAveragePrice', 
                                        item.get('Price', 0)))
                    try:
                        price_val = float(ref_price) if ref_price and ref_price != 'null' and ref_price != '' else 0
                        volume_val = float(volumes) if volumes and volumes != 'null' and volumes != '' else 0
                        
                        normalized_item = {
                            'date': date_val,
                            'type': type_val,
                            'price': price_val,
                            'volume': volume_val
                        }
                        parsed_data.append(normalized_item)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping environmental item due to conversion error: {e}")
                        continue
                    normalized_item = {
                        'date': date_val,
                        'type': type_val,
                        'price': float(ref_price) if ref_price else 0,
                        'volume': float(volumes) if volumes else 0
                    }
                    parsed_data.append(normalized_item)
        
        return parsed_data
    
    if isinstance(result, dict):
        parsed_data = []
        
        if 'Prices' in result:
            prices_data = result['Prices']
            if isinstance(prices_data, list):
                return parse_gme_response(prices_data, market_type)
        
        if 'Results' in result:
            return parse_gme_response(result['Results'], market_type)
        
        if 'Data' in result:
            return parse_gme_response(result['Data'], market_type)
        
        for key in result.keys():
            if isinstance(result[key], list) and len(result[key]) > 0:
                return parse_gme_response(result[key], market_type)
        
        return parsed_data
    
    return []

def get_client():
    username = os.getenv("GME_USERNAME")
    password = os.getenv("GME_PASSWORD")
    if not username or not password:
        raise Exception("GME credentials not set")
    return GMEClient(username, password)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/test')
def test():
    return render_template('test.html')

@main_bp.route('/api/markets', methods=['GET'])
def get_markets():
    try:
        return jsonify({
            "electricity": [
                {"id": "MGP", "name": "MGP - Day-Ahead Market"},
                {"id": "MI1", "name": "MI1 - Intraday Session 1"},
                {"id": "MI2", "name": "MI2 - Intraday Session 2"},
                {"id": "MI3", "name": "MI3 - Intraday Session 3"},
                {"id": "MI4", "name": "MI4 - Intraday Session 4"},
                {"id": "MI5", "name": "MI5 - Intraday Session 5"},
                {"id": "MI6", "name": "MI6 - Intraday Session 6"},
                {"id": "MI7", "name": "MI7 - Intraday Session 7"},
                {"id": "MSD", "name": "MSD - Ancillary Services Market"},
                {"id": "MB", "name": "MB - Balancing Market"}
            ],
            "gas": [
                {"id": "MGP-GAS", "name": "MGP-GAS - Day-Ahead Gas Market"},
                {"id": "MI-GAS", "name": "MI-GAS - Intraday Gas Market"},
                {"id": "MI-GAS1", "name": "MI-GAS1 - Gas Intraday Session 1"},
                {"id": "MI-GAS2", "name": "MI-GAS2 - Gas Intraday Session 2"},
                {"id": "MI-GAS3", "name": "MI-GAS3 - Gas Intraday Session 3"},
                {"id": "MGS", "name": "MGS - Gas Storage Market"}
            ],
            "environmental": [
                {"id": "TEE", "name": "TEE - Energy Efficiency Certificates"},
                {"id": "GO", "name": "GO - Guarantees of Origin"},
                {"id": "CV", "name": "CV - Green Certificates"}
            ]
        })
        
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@main_bp.route('/api/price-data', methods=['POST'])
def get_price_data():
    try:
        data = request.json
        market_type = data.get('type')
        market = data.get('market')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        logger.info(f"Fetching data: type={market_type}, market={market}, dates={start_date_str} to {end_date_str}")
        
        if not all([market_type, market, start_date_str, end_date_str]):
            return jsonify({"error": "Missing parameters"}), 400
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        all_results = []
        current_date = start_date
        
        client = get_client()
        login_success = client.login()
        
        if not login_success:
            logger.error("GME API login failed")
            return jsonify({"error": "GME API authentication failed. Please check credentials in .env file."}), 401
        
        logger.info("GME API login successful")
        
        while current_date <= end_date:
            result = None
            try:
                if market_type == 'electricity':
                    if market == 'MB':
                        result = client.get_mb_results(current_date)
                    elif market == 'MSD':
                        result = client.get_electricity_prices(market, current_date)
                    else:
                        result = client.get_electricity_prices(market, current_date)
                elif market_type == 'gas':
                    result = client.get_gas_prices(market, current_date)
                elif market_type == 'environmental':
                    result = client.get_environmental_data(market, current_date)
                
                logger.info(f"Raw API response for {current_date}: type={type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                
                parsed_result = parse_gme_response(result, market_type)
                
                logger.info(f"Parsed data for {current_date}: {len(parsed_result) if isinstance(parsed_result, list) else 0} items")
                
                if parsed_result and isinstance(parsed_result, list):
                    for item in parsed_result:
                        if isinstance(item, dict):
                            if 'date' not in item or not item['date']:
                                item['date'] = current_date.strftime("%Y-%m-%d")
                    all_results.extend(parsed_result)
            except Exception as date_error:
                logger.warning(f"Error fetching data for {current_date}: {str(date_error)}")
            
            current_date += timedelta(days=1)
        
        if all_results:
            logger.info(f"Total results: {len(all_results)}")
            return jsonify({"data": all_results, "count": len(all_results)})
        else:
            logger.warning("No data found for the specified date range")
            return jsonify({"error": "No data found for the specified date range. Try a different date or market."}), 404
    
    except Exception as e:
        logger.error(f"Error in get_price_data: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@main_bp.route('/api/forecast', methods=['POST'])
def forecast():
    try:
        data = request.json
        history = data.get('history', [])
        forecast_days = data.get('days', 2)
        
        if not history:
            return jsonify({"error": "No historical data provided"}), 400
        
        forecast_data = train_and_predict(history, forecast_days=forecast_days)
        return jsonify({"forecast": forecast_data, "count": len(forecast_data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route('/api/export', methods=['POST'])
def export_excel():
    try:
        data = request.json
        rows = data.get('rows', [])
        filename = data.get('filename', 'gme_data.xlsx')
        
        if not rows:
            return jsonify({"error": "No data to export"}), 400
        
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Market Data')
            
            worksheet = writer.sheets['Market Data']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

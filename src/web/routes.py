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
                    if zone == 'PUN':
                        normalized_item = {
                            'date': item.get('FlowDate', item.get('date', '')),
                            'interval': int(item.get('Hour', item.get('hour', item.get('interval', 1)))),
                            'price': float(item.get('Price', item.get('price', 0))),
                            'zone': zone
                        }
                        parsed_data.append(normalized_item)
        
        elif market_type == 'gas':
            for item in result:
                if isinstance(item, dict):
                    normalized_item = {
                        'date': item.get('FlowDate', item.get('date', '')),
                        'interval': int(item.get('Hour', item.get('hour', item.get('interval', 1)))),
                        'price': float(item.get('Price', item.get('price', 0)))
                    }
                    parsed_data.append(normalized_item)
        
        elif market_type == 'environmental':
            parsed_data = result
        
        return parsed_data
    
    if isinstance(result, dict):
        parsed_data = []
        
        if 'Prices' in result:
            prices_data = result['Prices']
            if isinstance(prices_data, list):
                return parse_gme_response(prices_data, market_type)
        
        if 'Results' in result:
            return parse_gme_response(result['Results'], market_type)
        
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
                {"id": "MI1", "name": "MI1 - First Intraday Session"},
                {"id": "MI2", "name": "MI2 - Second Intraday Session"},
                {"id": "MI3", "name": "MI3 - Third Intraday Session"},
                {"id": "MI4", "name": "MI4 - Fourth Intraday Session"},
                {"id": "MI5", "name": "MI5 - Fifth Intraday Session"},
                {"id": "MI6", "name": "MI6 - Sixth Intraday Session"},
                {"id": "MI7", "name": "MI7 - Seventh Intraday Session"},
                {"id": "MPEG", "name": "MPEG - Platform for Physical Delivery"}
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

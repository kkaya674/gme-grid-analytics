python src/main.py --date 2025-12-23
python src/analyze_congestion.py --date 2025-12-23
python src/analyze_balancing.py --date 2025-12-23
python src/animate_flows.py --date 2025-12-23 --output workspace/mgp_animation.gif
python src/plot_gme.py --market MGP --hour 12 --date 2025-12-23
python src/plot_flows.py --date 2025-12-23 --hour 12
python main.py --date 2025-12-20
python analyze_congestion.py --date 2025-12-20
python analyze_balancing.py --date 2025-12-20
python animate_flows.py --date 2025-12-20 --output analysis/mgp_animation.gif
python plot_gme.py --market MGP --hour 12 --date 2025-12-20
python plot_flows.py --date 2025-12-20 --hour 12
"""
Create HTML viewer for all trade charts
"""
import pandas as pd
from pathlib import Path
import base64

def calculate_slope_allocation_conservative(slope, base_size=10000):
    """Conservative allocation - skip weak trades < 1.0%"""
    if slope >= 5.0:
        return base_size * 2.0
    elif slope >= 3.0:
        return base_size * 1.5
    elif slope >= 2.0:
        return base_size * 1.2
    elif slope >= 1.0:
        return base_size * 1.0
    else:
        return 0.0

def create_html_viewer():
    """Create interactive HTML viewer for all trade charts"""

    results_dir = Path("results")
    charts_dir = results_dir / "trade_charts"

    # Load trades data
    csv_files = sorted(results_dir.glob("trades_with_slopes_2.2a_*.csv"))
    df_trades = pd.read_csv(csv_files[-1])

    # Apply conservative allocation
    df_trades['position_size'] = df_trades['entry_slope_5p_0la'].apply(
        calculate_slope_allocation_conservative
    )
    df_conservative = df_trades[df_trades['position_size'] > 0].copy()

    # Get last 25 trades
    df_conservative['exit_date'] = pd.to_datetime(df_conservative['exit_date'])
    df_last_25 = df_conservative.nlargest(25, 'exit_date').reset_index(drop=True)

    # Get all chart files
    chart_files = sorted(charts_dir.glob("trade_*.png"))

    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Last 25 Trades - Conservative Allocation Strategy</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
        }

        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        .subtitle {
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 1.1em;
        }

        .stats-bar {
            display: flex;
            justify-content: space-around;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            color: white;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .sort-controls select {
            padding: 10px 15px;
            border: 2px solid #667eea;
            border-radius: 5px;
            font-size: 1em;
            cursor: pointer;
            background: white;
        }

        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }

        .trade-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            border: 2px solid #e0e0e0;
        }

        .trade-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        }

        .trade-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
        }

        .trade-header h3 {
            font-size: 1.5em;
            margin-bottom: 5px;
        }

        .trade-dates {
            font-size: 0.9em;
            opacity: 0.9;
        }

        .trade-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            padding: 15px;
            background: #f8f9fa;
        }

        .metric {
            text-align: center;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }

        .metric-value {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 3px;
        }

        .metric-value.positive {
            color: #27ae60;
        }

        .metric-value.negative {
            color: #e74c3c;
        }

        .metric-label {
            font-size: 0.8em;
            color: #7f8c8d;
            text-transform: uppercase;
        }

        .chart-image {
            width: 100%;
            height: auto;
            display: block;
            cursor: pointer;
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }

        .modal-content {
            margin: 2% auto;
            display: block;
            max-width: 95%;
            max-height: 95%;
        }

        .close {
            position: absolute;
            top: 30px;
            right: 50px;
            color: #f1f1f1;
            font-size: 50px;
            font-weight: bold;
            cursor: pointer;
        }

        .close:hover {
            color: #bbb;
        }

        .position-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }

        .pos-2x { background: #27ae60; color: white; }
        .pos-15x { background: #3498db; color: white; }
        .pos-12x { background: #f39c12; color: white; }
        .pos-1x { background: #95a5a6; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Last 25 Trades - Conservative Allocation</h1>
        <div class="subtitle">4-Day Bar Strategy with Slope-Based Position Sizing</div>

        <div class="stats-bar">
            <div class="stat">
                <div class="stat-value">25</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="total-pnl">$0</div>
                <div class="stat-label">Total P&L</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="avg-pnl">$0</div>
                <div class="stat-label">Avg P&L</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="win-rate">0%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="avg-slope">0%</div>
                <div class="stat-label">Avg Slope</div>
            </div>
        </div>

        <div class="controls">
            <div class="sort-controls">
                <label for="sort-by">Sort by: </label>
                <select id="sort-by" onchange="sortTrades()">
                    <option value="trade-num">Trade Number</option>
                    <option value="pnl-desc">P&L (Highest First)</option>
                    <option value="pnl-asc">P&L (Lowest First)</option>
                    <option value="slope-desc">Slope (Highest First)</option>
                    <option value="slope-asc">Slope (Lowest First)</option>
                    <option value="size-desc">Position Size (Largest First)</option>
                </select>
            </div>
            <div style="color: #7f8c8d;">
                Click on any chart to view full size
            </div>
        </div>

        <div class="grid-container" id="trades-grid">
"""

    # Add trade cards
    for i, (idx, trade) in enumerate(df_last_25.iterrows(), 1):
        symbol = trade['symbol']
        pnl = trade['pnl']
        slope = trade['entry_slope_5p_0la']
        position_mult = trade['position_size'] / 10000
        entry_date = pd.to_datetime(trade['entry_date']).strftime('%Y-%m-%d')
        exit_date = pd.to_datetime(trade['exit_date']).strftime('%Y-%m-%d')

        # Find corresponding chart file
        chart_file = charts_dir / f"trade_{i:02d}_{symbol}_{exit_date}.png"

        # Position size badge
        if position_mult == 2.0:
            pos_class = "pos-2x"
            pos_label = "2.0x"
        elif position_mult == 1.5:
            pos_class = "pos-15x"
            pos_label = "1.5x"
        elif position_mult == 1.2:
            pos_class = "pos-12x"
            pos_label = "1.2x"
        else:
            pos_class = "pos-1x"
            pos_label = "1.0x"

        pnl_class = "positive" if pnl > 0 else "negative"
        pnl_sign = "+" if pnl > 0 else ""

        html_content += f"""
            <div class="trade-card"
                 data-pnl="{pnl}"
                 data-slope="{slope}"
                 data-size="{position_mult}"
                 data-trade-num="{i}">
                <div class="trade-header">
                    <h3>
                        {symbol}
                        <span class="position-badge {pos_class}">{pos_label}</span>
                    </h3>
                    <div class="trade-dates">{entry_date} → {exit_date}</div>
                </div>
                <div class="trade-metrics">
                    <div class="metric">
                        <div class="metric-value {pnl_class}">{pnl_sign}${pnl:,.0f}</div>
                        <div class="metric-label">P&L</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{slope:.2f}%</div>
                        <div class="metric-label">Slope</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{position_mult:.1f}x</div>
                        <div class="metric-label">Position</div>
                    </div>
                </div>
                <img src="{chart_file.name}" alt="{symbol} Trade Chart" class="chart-image" onclick="openModal(this.src)">
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- Modal for full-size image -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="close">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        // Calculate and display summary statistics
        function updateStats() {
            const cards = document.querySelectorAll('.trade-card');
            let totalPnl = 0;
            let winners = 0;
            let totalSlope = 0;

            cards.forEach(card => {
                const pnl = parseFloat(card.dataset.pnl);
                const slope = parseFloat(card.dataset.slope);
                totalPnl += pnl;
                if (pnl > 0) winners++;
                totalSlope += slope;
            });

            document.getElementById('total-pnl').textContent =
                '$' + totalPnl.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
            document.getElementById('avg-pnl').textContent =
                '$' + (totalPnl / cards.length).toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
            document.getElementById('win-rate').textContent =
                ((winners / cards.length) * 100).toFixed(1) + '%';
            document.getElementById('avg-slope').textContent =
                (totalSlope / cards.length).toFixed(2) + '%';
        }

        // Sort trades
        function sortTrades() {
            const grid = document.getElementById('trades-grid');
            const cards = Array.from(grid.children);
            const sortBy = document.getElementById('sort-by').value;

            cards.sort((a, b) => {
                switch(sortBy) {
                    case 'pnl-desc':
                        return parseFloat(b.dataset.pnl) - parseFloat(a.dataset.pnl);
                    case 'pnl-asc':
                        return parseFloat(a.dataset.pnl) - parseFloat(b.dataset.pnl);
                    case 'slope-desc':
                        return parseFloat(b.dataset.slope) - parseFloat(a.dataset.slope);
                    case 'slope-asc':
                        return parseFloat(a.dataset.slope) - parseFloat(b.dataset.slope);
                    case 'size-desc':
                        return parseFloat(b.dataset.size) - parseFloat(a.dataset.size);
                    case 'trade-num':
                    default:
                        return parseInt(a.dataset.tradeNum) - parseInt(b.dataset.tradeNum);
                }
            });

            cards.forEach(card => grid.appendChild(card));
        }

        // Modal functions
        function openModal(src) {
            document.getElementById('imageModal').style.display = 'block';
            document.getElementById('modalImage').src = src;
        }

        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }

        // Initialize
        updateStats();
    </script>
</body>
</html>
"""

    # Save HTML file
    output_file = results_dir / "trade_charts" / "trade_viewer.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n[SAVED] {output_file}")
    print(f"\nOpen this file in your web browser to view all 25 trades:")
    print(f"file:///{output_file.absolute()}")

    return output_file

if __name__ == "__main__":
    create_html_viewer()

import logging
from typing import Dict, Any, List
from ..models.post import ChartData

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Generates HTML/CSS charts for posts"""
    
    def __init__(self):
        self.color_palette = [
            "#0366d6", "#2ea44f", "#f66a0a", "#8b5cf6",
            "#ec4899", "#06b6d4", "#84cc16", "#ef4444"
        ]
    
    def generate_chart_html(self, chart: ChartData) -> str:
        """Generate HTML for a chart based on its type"""
        try:
            if chart.chart_type == "pie":
                return self._generate_pie_chart(chart)
            elif chart.chart_type == "bar":
                return self._generate_bar_chart(chart)
            elif chart.chart_type == "progress":
                return self._generate_progress_chart(chart)
            elif chart.chart_type == "line":
                return self._generate_line_chart(chart)
            else:
                return self._generate_fallback_chart(chart)
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return self._generate_fallback_chart(chart)
    
    def _generate_pie_chart(self, chart: ChartData) -> str:
        """Generate a CSS-based pie chart"""
        labels = chart.data.get("labels", [])
        values = chart.data.get("values", [])
        
        if not labels or not values or len(labels) != len(values):
            return self._generate_fallback_chart(chart)
        
        total = sum(values)
        if total == 0:
            return self._generate_fallback_chart(chart)
        
        # Generate pie chart using CSS conic-gradient
        segments = []
        current_angle = 0
        
        for i, (label, value) in enumerate(zip(labels, values)):
            percentage = (value / total) * 100
            color = self.color_palette[i % len(self.color_palette)]
            
            segments.append({
                "label": label,
                "value": value,
                "percentage": percentage,
                "color": color,
                "start_angle": current_angle,
                "end_angle": current_angle + percentage
            })
            
            current_angle += percentage
        
        # Build gradient string
        gradient_parts = []
        for segment in segments:
            gradient_parts.append(f"{segment['color']} {segment['start_angle']}% {segment['end_angle']}%")
        
        gradient = "conic-gradient(" + ", ".join(gradient_parts) + ")"
        
        # Generate legend
        legend_html = ""
        for segment in segments:
            legend_html += f"""
            <div class="legend-item">
                <div class="legend-color" style="background-color: {segment['color']}"></div>
                <span class="legend-label">{segment['label']}</span>
                <span class="legend-value">({segment['value']})</span>
            </div>
            """
        
        html = f"""
        <div class="chart-container pie-chart">
            <h4 class="chart-title">{chart.title}</h4>
            {f'<p class="chart-description">{chart.description}</p>' if chart.description else ''}
            <div class="pie-chart-wrapper">
                <div class="pie-chart-circle" style="background: {gradient}"></div>
                <div class="pie-chart-legend">
                    {legend_html}
                </div>
            </div>
        </div>
        
        <style>
        .pie-chart {{
            text-align: center;
            margin: 20px 0;
        }}
        .pie-chart-wrapper {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .pie-chart-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            flex-shrink: 0;
        }}
        .pie-chart-legend {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }}
        .legend-label {{
            font-weight: 500;
        }}
        .legend-value {{
            color: #666;
        }}
        </style>
        """
        
        return html
    
    def _generate_bar_chart(self, chart: ChartData) -> str:
        """Generate a CSS-based bar chart"""
        labels = chart.data.get("labels", [])
        values = chart.data.get("values", [])
        
        if not labels or not values or len(labels) != len(values):
            return self._generate_fallback_chart(chart)
        
        max_value = max(values) if values else 1
        
        bars_html = ""
        for i, (label, value) in enumerate(zip(labels, values)):
            height_percentage = (value / max_value) * 100
            color = self.color_palette[i % len(self.color_palette)]
            
            bars_html += f"""
            <div class="bar-item">
                <div class="bar-container">
                    <div class="bar-fill" style="height: {height_percentage}%; background-color: {color};">
                        <span class="bar-value">{value}</span>
                    </div>
                </div>
                <div class="bar-label">{label}</div>
            </div>
            """
        
        html = f"""
        <div class="chart-container bar-chart">
            <h4 class="chart-title">{chart.title}</h4>
            {f'<p class="chart-description">{chart.description}</p>' if chart.description else ''}
            <div class="bar-chart-wrapper">
                {bars_html}
            </div>
        </div>
        
        <style>
        .bar-chart {{
            margin: 20px 0;
        }}
        .bar-chart-wrapper {{
            display: flex;
            align-items: end;
            gap: 12px;
            padding: 20px 0;
            min-height: 120px;
        }}
        .bar-item {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .bar-container {{
            height: 100px;
            width: 100%;
            max-width: 40px;
            display: flex;
            align-items: end;
            justify-content: center;
        }}
        .bar-fill {{
            width: 100%;
            border-radius: 4px 4px 0 0;
            position: relative;
            min-height: 4px;
            display: flex;
            align-items: end;
            justify-content: center;
        }}
        .bar-value {{
            color: white;
            font-size: 10px;
            font-weight: bold;
            padding: 2px;
        }}
        .bar-label {{
            margin-top: 8px;
            font-size: 11px;
            text-align: center;
            color: #666;
        }}
        </style>
        """
        
        return html
    
    def _generate_progress_chart(self, chart: ChartData) -> str:
        """Generate a progress bar chart"""
        percentage = chart.data.get("percentage", 0)
        label = chart.data.get("label", "Progress")
        
        # Ensure percentage is within bounds
        percentage = max(0, min(100, percentage))
        
        # Choose color based on percentage
        if percentage >= 80:
            color = "#2ea44f"  # Green
        elif percentage >= 60:
            color = "#f66a0a"  # Orange
        else:
            color = "#0366d6"  # Blue
        
        html = f"""
        <div class="chart-container progress-chart">
            <h4 class="chart-title">{chart.title}</h4>
            {f'<p class="chart-description">{chart.description}</p>' if chart.description else ''}
            <div class="progress-wrapper">
                <div class="progress-label-row">
                    <span class="progress-label">{label}</span>
                    <span class="progress-percentage">{percentage}%</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: {percentage}%; background-color: {color};"></div>
                </div>
            </div>
        </div>
        
        <style>
        .progress-chart {{
            margin: 20px 0;
        }}
        .progress-wrapper {{
            width: 100%;
        }}
        .progress-label-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        .progress-label {{
            font-weight: 500;
            color: #24292f;
        }}
        .progress-percentage {{
            font-weight: 600;
            color: #0366d6;
        }}
        .progress-bar-container {{
            width: 100%;
            height: 12px;
            background-color: #ebeef0;
            border-radius: 6px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            border-radius: 6px;
            transition: width 0.3s ease;
        }}
        </style>
        """
        
        return html
    
    def _generate_line_chart(self, chart: ChartData) -> str:
        """Generate a simple line chart using CSS"""
        labels = chart.data.get("labels", [])
        values = chart.data.get("values", [])
        
        if not labels or not values or len(labels) != len(values):
            return self._generate_fallback_chart(chart)
        
        max_value = max(values) if values else 1
        min_value = min(values) if values else 0
        
        # Generate points for the line
        points = []
        for i, value in enumerate(values):
            x = (i / (len(values) - 1)) * 100  # X position as percentage
            y = 100 - ((value - min_value) / (max_value - min_value)) * 100  # Y position (inverted)
            points.append(f"{x}% {y}%")
        
        points_str = ", ".join(points)
        
        # Generate value labels
        value_labels = ""
        for i, (label, value) in enumerate(zip(labels, values)):
            x_pos = (i / (len(values) - 1)) * 100
            value_labels += f"""
            <div class="line-point" style="left: {x_pos}%; bottom: {((value - min_value) / (max_value - min_value)) * 100}%;">
                <span class="point-value">{value}</span>
            </div>
            <div class="line-label" style="left: {x_pos}%;">{label}</div>
            """
        
        html = f"""
        <div class="chart-container line-chart">
            <h4 class="chart-title">{chart.title}</h4>
            {f'<p class="chart-description">{chart.description}</p>' if chart.description else ''}
            <div class="line-chart-wrapper">
                <div class="line-chart-area">
                    <div class="line-path" style="clip-path: polygon({points_str}, 100% 100%, 0% 100%);"></div>
                    {value_labels}
                </div>
            </div>
        </div>
        
        <style>
        .line-chart {{
            margin: 20px 0;
        }}
        .line-chart-wrapper {{
            position: relative;
            height: 150px;
            padding: 20px 0;
        }}
        .line-chart-area {{
            position: relative;
            height: 100px;
            border-bottom: 1px solid #ebeef0;
            border-left: 1px solid #ebeef0;
        }}
        .line-path {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, #0366d620, #0366d610);
            border-top: 2px solid #0366d6;
        }}
        .line-point {{
            position: absolute;
            width: 8px;
            height: 8px;
            background-color: #0366d6;
            border-radius: 50%;
            transform: translate(-50%, 50%);
        }}
        .point-value {{
            position: absolute;
            bottom: 12px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10px;
            font-weight: 600;
            color: #0366d6;
            background: white;
            padding: 2px 4px;
            border-radius: 2px;
            white-space: nowrap;
        }}
        .line-label {{
            position: absolute;
            bottom: -25px;
            transform: translateX(-50%);
            font-size: 11px;
            color: #666;
        }}
        </style>
        """
        
        return html
    
    def _generate_fallback_chart(self, chart: ChartData) -> str:
        """Generate a simple fallback chart when data is invalid"""
        html = f"""
        <div class="chart-container fallback-chart">
            <h4 class="chart-title">{chart.title}</h4>
            {f'<p class="chart-description">{chart.description}</p>' if chart.description else ''}
            <div class="chart-placeholder">
                <div class="placeholder-icon">📊</div>
                <p class="placeholder-text">Chart data not available</p>
            </div>
        </div>
        
        <style>
        .fallback-chart {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-placeholder {{
            padding: 40px 20px;
            background: #f6f8fa;
            border-radius: 6px;
            border: 1px dashed #d1d9e0;
        }}
        .placeholder-icon {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .placeholder-text {{
            color: #586069;
            font-size: 14px;
            margin: 0;
        }}
        </style>
        """
        
        return html
"""Cytoscape.js HTML Component Generator for Digital Archaeologist.

Generates a standalone, self-contained interactive Cytoscape.js visualization
with dark-mode obsidian styling, interactive node inspection, layout controls,
and animated edge flows.
"""

from __future__ import annotations

import json
from typing import Any


def generate_cytoscape_html(cytoscape_data: dict[str, Any], height: int = 680) -> str:
    """Generate interactive Cytoscape.js visualization HTML string.

    Args:
        cytoscape_data: Dictionary containing Cytoscape.js JSON structure:
                        { "elements": { "nodes": [...], "edges": [...] } }
        height: Height in pixels for the container iframe.

    Returns:
        Complete HTML document string ready for st.components.v1.html().
    """
    elements = cytoscape_data.get("elements", {})
    # If elements is already a flat list or dict with nodes/edges, ensure JSON serializable
    elements_json = json.dumps(elements)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Digital Archaeologist - Cytoscape Knowledge Graph</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.4/cytoscape.min.js"></script>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    body, html {{
      width: 100%;
      height: 100%;
      overflow: hidden;
      background-color: #0b0f19;
      color: #e2e8f0;
    }}
    #cy-wrapper {{
      position: relative;
      width: 100%;
      height: {height}px;
      background: radial-gradient(circle at 50% 50%, #111827 0%, #0b0f19 100%);
      border: 1px solid #1f2937;
      border-radius: 12px;
      overflow: hidden;
    }}
    #cy {{
      width: 100%;
      height: 100%;
      z-index: 1;
    }}
    /* Subtle dot grid pattern */
    #grid-overlay {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      background-image: radial-gradient(#374151 1px, transparent 1px);
      background-size: 24px 24px;
      opacity: 0.25;
      z-index: 0;
    }}
    /* Glassmorphism Toolbar */
    .toolbar {{
      position: absolute;
      top: 14px;
      left: 14px;
      z-index: 10;
      display: flex;
      gap: 6px;
      align-items: center;
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 6px 10px;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    }}
    .btn {{
      background: #1f2937;
      color: #f3f4f6;
      border: 1px solid #374151;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 4px;
    }}
    .btn:hover {{
      background: #374151;
      border-color: #4b5563;
      color: #ffffff;
      transform: translateY(-1px);
    }}
    .btn:active {{
      transform: translateY(0);
    }}
    .select-layout {{
      background: #1f2937;
      color: #f3f4f6;
      border: 1px solid #374151;
      padding: 5px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      outline: none;
      cursor: pointer;
    }}
    /* Node Legend */
    .legend {{
      position: absolute;
      bottom: 14px;
      left: 14px;
      z-index: 10;
      background: rgba(17, 24, 39, 0.88);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 8px 12px;
      display: flex;
      gap: 12px;
      font-size: 11px;
      color: #9ca3af;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .legend-color {{
      width: 10px;
      height: 10px;
      border-radius: 3px;
    }}
    /* Inspector Card Drawer */
    #inspector {{
      position: absolute;
      top: 14px;
      right: 14px;
      width: 320px;
      max-height: calc(100% - 28px);
      overflow-y: auto;
      z-index: 20;
      background: rgba(17, 24, 39, 0.94);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 10px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
      transition: all 0.2s ease;
    }}
    .inspector-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 10px;
      border-bottom: 1px solid #374151;
      padding-bottom: 8px;
    }}
    .inspector-title {{
      font-size: 15px;
      font-weight: 700;
      color: #f9fafb;
      word-break: break-all;
    }}
    .close-btn {{
      background: none;
      border: none;
      color: #9ca3af;
      font-size: 16px;
      cursor: pointer;
      padding: 0 4px;
    }}
    .close-btn:hover {{
      color: #f3f4f6;
    }}
    .tag {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .tag-entry {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }}
    .tag-module {{ background: rgba(6, 182, 212, 0.2); color: #38bdf8; border: 1px solid #0891b2; }}
    .tag-service {{ background: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid #7c3aed; }}
    .tag-config {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }}
    .tag-util {{ background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid #db2777; }}
    
    .prop-row {{
      margin-bottom: 8px;
      font-size: 12px;
    }}
    .prop-label {{
      color: #9ca3af;
      font-weight: 600;
      margin-bottom: 2px;
    }}
    .prop-value {{
      color: #e5e7eb;
      background: #111827;
      padding: 4px 6px;
      border-radius: 4px;
      border: 1px solid #1f2937;
      font-family: monospace;
      font-size: 11px;
      word-break: break-all;
    }}
    .quirk-box {{
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
      padding: 6px 8px;
      border-radius: 6px;
      font-size: 11px;
      margin-top: 4px;
      line-height: 1.4;
    }}
  </style>
</head>
<body>
  <div id="cy-wrapper">
    <div id="grid-overlay"></div>

    <!-- Controls Toolbar -->
    <div class="toolbar">
      <button class="btn" onclick="cy.zoom(cy.zoom() * 1.25); cy.center();" title="Zoom In">➕ Zoom</button>
      <button class="btn" onclick="cy.zoom(cy.zoom() * 0.8); cy.center();" title="Zoom Out">➖ Zoom</button>
      <button class="btn" onclick="cy.fit(null, 40);" title="Fit to View">⛶ Fit View</button>
      <button class="btn" onclick="runLayout();" title="Re-run physics layout">↺ Re-layout</button>
      <select class="select-layout" id="layoutSelect" onchange="runLayout();">
        <option value="cose" selected>Force-Directed (CoSE)</option>
        <option value="concentric">Concentric (Degree)</option>
        <option value="breadthfirst">Hierarchical (Tree)</option>
        <option value="circle">Circular</option>
        <option value="grid">Grid</option>
      </select>
    </div>

    <!-- Cytoscape Graph Canvas -->
    <div id="cy"></div>

    <!-- Legend -->
    <div class="legend">
      <div class="legend-item"><div class="legend-color" style="background:#10b981;"></div>Entrypoint</div>
      <div class="legend-item"><div class="legend-color" style="background:#06b6d4;"></div>Module</div>
      <div class="legend-item"><div class="legend-color" style="background:#8b5cf6;"></div>Service</div>
      <div class="legend-item"><div class="legend-color" style="background:#f59e0b;"></div>Config</div>
      <div class="legend-item"><div class="legend-color" style="background:#ec4899;"></div>Util</div>
    </div>

    <!-- Node Inspector Card -->
    <div id="inspector">
      <div class="inspector-header">
        <div class="inspector-title" id="insp-title">🔍 Click a Node</div>
        <button class="close-btn" onclick="document.getElementById('inspector').style.display='none';">&times;</button>
      </div>
      <div id="insp-body">
        <p style="font-size: 12px; color: #9ca3af;">Click on any node in the graph to inspect its symbols, import dependencies, and detected undocumented behaviors.</p>
      </div>
    </div>
  </div>

  <script>
    const rawElements = {elements_json};

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: rawElements,
      style: [
        // Default Node Style
        {{
          selector: 'node',
          style: {{
            'label': 'data(label)',
            'color': '#f3f4f6',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'text-background-opacity': 0.85,
            'text-background-color': '#111827',
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'background-color': '#06b6d4',
            'width': 'mapData(degree, 0, 10, 28, 48)',
            'height': 'mapData(degree, 0, 10, 28, 48)',
            'border-width': 2,
            'border-color': '#38bdf8',
            'transition-property': 'background-color, border-color, border-width, width, height',
            'transition-duration': '0.2s'
          }}
        }},
        // Entry Points (Emerald Glow)
        {{
          selector: 'node[type = "entrypoint"]',
          style: {{
            'background-color': '#10b981',
            'border-color': '#6ee7b7',
            'border-width': 3,
            'shape': 'diamond',
            'width': 44,
            'height': 44
          }}
        }},
        // Services / Handlers (Violet)
        {{
          selector: 'node[type = "service"]',
          style: {{
            'background-color': '#8b5cf6',
            'border-color': '#c084fc',
            'shape': 'round-rectangle'
          }}
        }},
        // Configs (Amber)
        {{
          selector: 'node[type = "config"]',
          style: {{
            'background-color': '#f59e0b',
            'border-color': '#fde68a',
            'shape': 'hexagon'
          }}
        }},
        // Utils (Pink)
        {{
          selector: 'node[type = "util"]',
          style: {{
            'background-color': '#ec4899',
            'border-color': '#fbcfe8'
          }}
        }},
        // Highlighted Node on Selection
        {{
          selector: 'node:selected, node.highlighted',
          style: {{
            'border-color': '#ffffff',
            'border-width': 4,
            'shadow-blur': 15,
            'shadow-color': '#ffffff',
            'shadow-opacity': 0.8
          }}
        }},
        // Edges
        {{
          selector: 'edge',
          style: {{
            'width': 2,
            'line-color': '#4b5563',
            'target-arrow-color': '#4b5563',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.1,
            'opacity': 0.7,
            'transition-property': 'line-color, width, opacity',
            'transition-duration': '0.2s'
          }}
        }},
        // Highlighted Edges
        {{
          selector: 'edge.highlighted',
          style: {{
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'width': 3.5,
            'opacity': 1.0
          }}
        }}
      ],
      layout: {{
        name: 'cose',
        animate: false,
        randomize: false,
        nodeRepulsion: 6000,
        idealEdgeLength: 80,
        nodeOverlap: 20
      }}
    }});

    // Layout runner
    function runLayout() {{
      const layoutName = document.getElementById('layoutSelect').value;
      const layoutOptions = {{
        name: layoutName,
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 50
      }};
      if (layoutName === 'cose') {{
        layoutOptions.nodeRepulsion = 7000;
        layoutOptions.idealEdgeLength = 90;
      }}
      cy.layout(layoutOptions).run();
    }}

    // Node click inspector logic
    cy.on('tap', 'node', function(evt) {{
      const node = evt.target;
      const d = node.data();

      // Highlight active node and its neighbors
      cy.elements().removeClass('highlighted');
      node.addClass('highlighted');
      node.connectedEdges().addClass('highlighted');
      node.neighborhood().nodes().addClass('highlighted');

      // Populate Inspector
      document.getElementById('inspector').style.display = 'block';
      document.getElementById('insp-title').innerText = d.filename || d.id;

      let tagClass = 'tag-module';
      if (d.type === 'entrypoint') tagClass = 'tag-entry';
      else if (d.type === 'service') tagClass = 'tag-service';
      else if (d.type === 'config') tagClass = 'tag-config';
      else if (d.type === 'util') tagClass = 'tag-util';

      let exportsHtml = (d.exports && d.exports.length > 0) 
        ? d.exports.map(s => `<span class="prop-value" style="display:inline-block; margin:2px;">${{s}}</span>`).join('')
        : '<span style="color:#6b7280; font-size:11px;">None declared</span>';

      let importsHtml = (d.imports && d.imports.length > 0)
        ? d.imports.map(i => `<span class="prop-value" style="display:inline-block; margin:2px;">${{i}}</span>`).join('')
        : '<span style="color:#6b7280; font-size:11px;">None detected</span>';

      let quirksHtml = '';
      if (d.undocumented_behaviors && d.undocumented_behaviors.length > 0) {{
        quirksHtml = `
          <div class="prop-row" style="margin-top:10px;">
            <div class="prop-label" style="color:#f87171;">⚠️ Undocumented Behaviors / Quirks:</div>
            ${{d.undocumented_behaviors.map(q => `<div class="quirk-box">⚡ ${{q}}</div>`).join('')}}
          </div>
        `;
      }}

      document.getElementById('insp-body').innerHTML = `
        <span class="tag ${{tagClass}}">${{d.type || 'module'}}</span>
        <div class="prop-row">
          <div class="prop-label">Full Path:</div>
          <div class="prop-value">${{d.path || d.id}}</div>
        </div>
        <div class="prop-row">
          <div class="prop-label">Language / Format:</div>
          <div class="prop-value">${{d.language || 'Unknown'}}</div>
        </div>
        <div class="prop-row">
          <div class="prop-label">Exported Symbols:</div>
          <div>${{exportsHtml}}</div>
        </div>
        <div class="prop-row">
          <div class="prop-label">Dependencies (Imports):</div>
          <div>${{importsHtml}}</div>
        </div>
        ${{quirksHtml}}
      `;
    }});

    // Reset highlights on background tap
    cy.on('tap', function(evt) {{
      if (evt.target === cy) {{
        cy.elements().removeClass('highlighted');
      }}
    }});

    // Initial fit
    setTimeout(() => {{
      cy.fit(null, 45);
    }}, 200);
  </script>
</body>
</html>"""
    return html_content

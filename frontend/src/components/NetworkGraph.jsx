import { useState, useRef, useEffect, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { ZoomIn, ZoomOut, RefreshCw, AlertCircle } from 'lucide-react';

export const NetworkGraph = ({ data, loading, height = 500 }) => {
  const fgRef = useRef();
  const containerRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 800, height });
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());

  // Size the canvas to its card (fgRef holds the graph API, not a DOM node).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const update = () => setDimensions({ width: el.clientWidth, height });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [height, loading, data]);

  // Spread the nodes out; the default forces pack a dense graph into a knot.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force('charge')?.strength(-320);
    fg.d3Force('link')?.distance(110);
    fg.d3ReheatSimulation?.();
  }, [data]);

  // Transform data for ForceGraph (memoised so hovering does not restart the layout)
  const transformedData = useMemo(() => ({
    nodes: (data?.nodes || []).map(node => ({
      id: node.id,
      name: node.name,
      group: node.group || 1,
      value: node.value || 1,
      revenue: node.revenue || 0,
      transactions: node.transactions || 0,
    })),
    links: (data?.links || []).map(link => ({
      source: link.source,
      target: link.target,
      value: link.value || 0.1,
      strength: link.strength || 1,
      transactions: link.transactions || 0,
    }))
  }), [data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[500px] bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">
            Loading network graph...
          </p>
        </div>
      </div>
    );
  }

  if (!data?.nodes || data.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[500px] bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="text-gray-400 dark:text-gray-500 mb-4">
          <AlertCircle className="h-12 w-12 mx-auto" />
        </div>
        <p className="text-gray-600 dark:text-gray-400 text-center px-4">
          No network data available. Try adjusting your filters or lowering the support threshold.
        </p>
      </div>
    );
  }

  const handleNodeHover = (node) => {
    if (node) {
      const connectedNodes = new Set();
      const connectedLinks = new Set();

      // Find connected nodes
      transformedData.links.forEach((link) => {
        if (link.source.id === node.id || link.target.id === node.id) {
          connectedLinks.add(link);
          if (link.source.id === node.id) connectedNodes.add(link.target);
          if (link.target.id === node.id) connectedNodes.add(link.source);
        }
      });

      setHighlightNodes(connectedNodes);
      setHighlightLinks(connectedLinks);
    } else {
      setHighlightNodes(new Set());
      setHighlightLinks(new Set());
    }
  };

  const handleZoomIn = () => {
    if (fgRef.current) {
      fgRef.current.zoom(1.2, 100);
    }
  };

  const handleZoomOut = () => {
    if (fgRef.current) {
      fgRef.current.zoom(0.8, 100);
    }
  };

  const handleReset = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400);
    }
  };

  const getNodeColor = (node) => {
    if (highlightNodes.has(node)) return '#3b82f6';
    const groups = {
      'Low Price': '#10b981',
      'Medium Price': '#f59e0b',
      'High Price': '#ef4444',
    };
    return groups[node.group] || '#6b7280';
  };

  const getLinkColor = (link) => {
    if (highlightLinks.has(link)) return '#3b82f6';
    return link.strength > 1.5 ? '#10b981' : link.strength > 1 ? '#f59e0b' : '#9ca3af';
  };

  const getNodeSize = (node) => {
    const baseSize = 5;
    const revenueFactor = Math.log10(node.revenue + 1) / 2;
    return baseSize + revenueFactor * 3;
  };

  return (
    <div ref={containerRef} className="relative bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="absolute top-4 right-4 z-10 flex space-x-2">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button
          onClick={handleReset}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Reset View"
        >
          <RefreshCw className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        </button>
      </div>

      <ForceGraph2D
        ref={fgRef}
        graphData={transformedData}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel={(node) => `
          ${node.name}
          Revenue: $${(node.revenue || 0).toFixed(2)}
          Transactions: ${node.transactions || 0}
        `}
        nodeColor={getNodeColor}
        nodeRelSize={6}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.name;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = highlightNodes.has(node) ? '#3b82f6' : getNodeColor(node);
          
          // Draw node
          ctx.beginPath();
          ctx.arc(node.x, node.y, getNodeSize(node), 0, 2 * Math.PI, false);
          ctx.fill();
          
          // Draw label
          if (globalScale > 0.5) {
            ctx.fillStyle = '#374151';
            ctx.fillText(label, node.x, node.y + getNodeSize(node) + fontSize);
          }
        }}
        linkColor={getLinkColor}
        linkWidth={(link) => (highlightLinks.has(link) ? 3 : link.value * 2)}
        onNodeHover={handleNodeHover}
        cooldownTime={2500}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 90)}
        d3VelocityDecay={0.3}
        warmupTicks={20}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
      />

      <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3">
        <div className="text-xs text-gray-600 dark:text-gray-400">
          <div className="flex items-center mb-2">
            <div className="w-3 h-3 rounded-full bg-gray-500 mr-2"></div>
            <span>Product Node (size = revenue)</span>
          </div>
          <div className="flex items-center mb-2">
            <div className="w-8 h-0.5 bg-green-500 mr-2"></div>
            <span>Strong Association (lift &gt; 1.5)</span>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-0.5 bg-gray-400 mr-2"></div>
            <span>Weak Association</span>
          </div>
        </div>
      </div>

      {/* Node info panel when hovering */}
      {Array.from(highlightNodes).length > 0 && (
        <div className="absolute top-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 max-w-xs">
          <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
            Connected Products
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {Array.from(highlightNodes).map((node, idx) => (
              <div key={idx} className="text-sm">
                <div className="font-medium text-gray-900 dark:text-white">
                  {node.name}
                </div>
                <div className="text-gray-600 dark:text-gray-400">
                  Revenue: ${(node.revenue || 0).toFixed(2)} • Transactions: {node.transactions || 0}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
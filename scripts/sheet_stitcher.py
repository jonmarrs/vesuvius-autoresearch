#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Graph-Based Sheet Stitching
Solves the "Winding Gap" problem by computationally assigning winding angles
to fragmented surface sheets.

Based on the formal problem definition:
villa/thaumato-anakalyptor/documentation/Sheet_Stitching_Problem_Definition.pdf
"""

import numpy as np
from collections import defaultdict
import json
import heapq
import os
import argparse

class SheetGraph:
    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(list)
        
    def add_node(self, node_id, features=None):
        self.nodes.add(node_id)
        
    def add_edge(self, u, v, weight=1.0, angle_delta=0.0):
        self.edges[u].append({'to': v, 'weight': weight, 'delta': angle_delta})
        self.edges[v].append({'to': u, 'weight': weight, 'delta': -angle_delta})

def assign_winding_angles_viterbi(graph: SheetGraph, start_node=None):
    """
    Assigns a winding angle function f: N -> R using a Viterbi-like shortest path / highest confidence approach.
    """
    if not graph.nodes:
        return {}
        
    if start_node is None:
        start_node = next(iter(graph.nodes))
        
    # Standard Dijkstra/Viterbi for max confidence paths
    angles = {start_node: 0.0}
    visited = {start_node}
    
    # Priority queue: (-confidence, node, current_angle)
    # Using heapq for O(log N) operations instead of O(N log N) sorting
    queue = [(-1.0, start_node, 0.0)]
    
    while queue:
        conf, u, current_angle = heapq.heappop(queue)
        
        for edge in graph.edges[u]:
            v = edge['to']
            if v not in visited:
                visited.add(v)
                new_angle = current_angle + edge['delta']
                angles[v] = new_angle
                # heapq is a min-heap, so we keep conf negative for max confidence
                heapq.heappush(queue, (conf * edge['weight'], v, new_angle))
                
    return angles

def assign_winding_angles_random_walk(graph: SheetGraph, num_walks=2000):
    """
    Assigns winding angles using a Random Walk approach.
    By traversing the graph randomly and accumulating angle deltas, we can build a distribution
    of angle estimates for each node. The median of this distribution provides a robust consensus
    that naturally ignores outlier edges (incorrect segment connections).
    """
    if not graph.nodes:
        return {}
        
    start_node = next(iter(graph.nodes))
    angle_samples = defaultdict(list)
    angle_samples[start_node].append(0.0)
    
    nodes = list(graph.nodes)
    walk_length = max(20, len(nodes))
    
    for _ in range(num_walks):
        current_node = start_node
        current_angle = 0.0
        
        for _ in range(walk_length):
            neighbors = graph.edges[current_node]
            if not neighbors:
                break
                
            # Randomly select a neighbor, weighted by edge confidence
            weights = [max(edge['weight'], 0.01) for edge in neighbors]
            total_weight = sum(weights)
            probs = [w / total_weight for w in weights]
            
            chosen_idx = np.random.choice(len(neighbors), p=probs)
            edge = neighbors[chosen_idx]
            
            current_node = edge['to']
            current_angle += edge['delta']
            angle_samples[current_node].append(current_angle)
            
    # Consensus: Compute the median angle for each node
    final_angles = {}
    
    # Fallback to Viterbi for disconnected nodes or nodes never reached
    viterbi_fallback = assign_winding_angles_viterbi(graph, start_node=start_node)
    
    for node in graph.nodes:
        if angle_samples[node]:
            # Median is robust against walks that took "impossible" paths across the winding gap
            final_angles[node] = float(np.median(angle_samples[node]))
        else:
            final_angles[node] = viterbi_fallback.get(node, 0.0)
            
    return final_angles

def load_graph_from_pkl(pkl_path):
    import sys
    sys.path.append('villa/thaumato-anakalyptor')
    from ThaumatoAnakalyptor.instances_to_graph import load_graph
    
    thaumato_graph = load_graph(pkl_path)
    graph = SheetGraph()
    for node_id in thaumato_graph.nodes:
        graph.add_node(node_id)
    for u in thaumato_graph.edges:
        for v in thaumato_graph.edges[u]:
            edge_data = thaumato_graph.edges[u][v]
            # Assuming edge_data contains 'certainty' and 'k' (angle difference)
            weight = edge_data.get('certainty', 1.0)
            angle_delta = edge_data.get('k', 0.0)
            graph.add_edge(u, v, weight=weight, angle_delta=angle_delta)
    return graph, thaumato_graph

def main():
    parser = argparse.ArgumentParser(description="Graph-Based Sheet Stitching")
    parser.add_argument("--input_graph", type=str, help="Path to input graph JSON or PKL", required=False)
    parser.add_argument("--output", type=str, default="winding_angles.json", help="Output JSON or PKL path")
    parser.add_argument("--algorithm", type=str, choices=['viterbi', 'random_walk'], default='viterbi')
    args = parser.parse_args()
    
    graph = SheetGraph()
    thaumato_graph = None
    
    if args.input_graph and os.path.exists(args.input_graph):
        if args.input_graph.endswith(".pkl"):
            print(f"Loading PKL graph from {args.input_graph}...")
            graph, thaumato_graph = load_graph_from_pkl(args.input_graph)
        else:
            with open(args.input_graph, 'r') as f:
                data = json.load(f)
                for node in data.get('nodes', []):
                    graph.add_node(node['id'])
                for edge in data.get('edges', []):
                    graph.add_edge(edge['u'], edge['v'], edge.get('weight', 1.0), edge.get('angle_delta', 0.0))
    else:
        print("No input graph provided or file not found. Generating dummy graph for testing.")
        # Dummy graph representing fragmented sheets wrapping around a scroll
        for i in range(10):
            graph.add_node(i)
        for i in range(9):
            # Sheets connected sequentially with a slight angle delta
            graph.add_edge(i, i+1, weight=0.9, angle_delta=0.1)
            
    if args.algorithm == 'viterbi':
        angles = assign_winding_angles_viterbi(graph)
    else:
        angles = assign_winding_angles_random_walk(graph)
        
    print(f"Assigned winding angles for {len(angles)} nodes using {args.algorithm}.")
    
    if args.output.endswith(".pkl") and thaumato_graph is not None:
        for node_id, angle in angles.items():
            thaumato_graph.nodes_f[node_id] = angle
        print(f"Saving modified PKL graph to {args.output}...")
        thaumato_graph.save_graph(args.output)
    else:
        with open(args.output, 'w') as f:
            json.dump(angles, f, indent=4)
        print(f"Results written to {args.output}")

if __name__ == "__main__":
    main()

var network;
var allNodes, allEdges;
var highlightActive = false;
// It is required that MIN_NODE_SIZE < 0.80 * MAX_NODE_SIZE
var MIN_NODE_SIZE = 30,
    MAX_NODE_SIZE = 100
    MIN_EDGE_WIDTH = 1,
    MAX_EDGE_WIDTH = 25;

function redrawAll(container='networkCanvas') {

    var container = document.getElementById(container);
    var data = {
        nodes: nodesDataset,
        edges: edgesDataset
    }

    var numNodes = nodesDataset.length;
    var min_node_size = MIN_NODE_SIZE,
        max_node_size = MAX_NODE_SIZE;

    // for small graphs
    if (numNodes < 0.50 * MAX_NODE_SIZE) {
        min_node_size = Math.round(0.50 * MIN_NODE_SIZE);
        max_node_size = Math.round(0.50 * MAX_NODE_SIZE);
    } else if (numNodes < 0.25 * MAX_NODE_SIZE) {
        min_node_size = Math.round(0.25 * MIN_NODE_SIZE);
        max_node_size = Math.round(0.25 * MAX_NODE_SIZE);
    }

    var options = {
        nodes: {
            shape: 'dot',
            scaling: {
                min: min_node_size,
                max: max_node_size,
                label: {
                    // originall 8, 30
                    min: 20,
                    max: 60,
                    drawThreshold: 5,
                    maxVisible: 50
                }
            },
            font: {
                size: 12,
                face: 'Tahoma'
            }
        },
        edges: {
            scaling: {
                min: MIN_EDGE_WIDTH,
                max: MAX_EDGE_WIDTH
            },
            // width: 1.0,
            color: {
                inherit: 'from'
            },
            smooth: {
                // type: 'continuous'
                enabled: false
            }
        },
        // physics: false,
        physics: {
            forceAtlas2Based: {
                gravitationalConstant: -200,
                centralGravity: 0.005,
                springLength: 200,
                springConstant: 0.018
            },
            maxVelocity: 146,
            solver: 'forceAtlas2Based',
            timestep: 0.35,
            stabilization: {
                iterations: 150
            }
        },
        interaction: {
            tooltipDelay: 200,
            hideEdgesOnDrag: true,
            hover: true
        }
        // },
        // configure: {
        //     // filter: 'nodes,edges'
        //     filter: function (option, path) {
        //         if (path.indexOf('physics') !== -1) {
        //             return true;
        //         }
        //         if (path.indexOf('smooth') !== -1 || option === 'smooth') {
        //             return true;
        //         }
        //         return false;
        //     },
        //     container: document.getElementById('dev-ops')
        // }
    };

    // get a JSON object
    allNodes = nodesDataset.get({
        returnType: "Object"
    });

    allEdges = edgesDataset.get({
        returnType: "Object"
    });

    network = new vis.Network(container, data, options);

    network.on('click', neighbourhoodHighlight);
    network.on('doubleClick', resolveDoubleClick);
    network.on('hoverNode', resolveHoverNode);
}

function resolveDoubleClick(params) {
    console.log(params.nodes);
    if (params.nodes.length == 0) {
        return;
    }
    var node_id = String(params.nodes[0]);
    fetch_node_info(node_id);
}

function resolveHoverNode(params) {
    var selectedNodeID = params['node'];
    var selectedNode = allNodes[selectedNodeID];
    if (!selectedNode.hasOwnProperty('shape')) {
        return;
    }
    var group;
    if (selectedNode['shape'] === 'star') {
        group = selectedNode['group'];
    } else {
        return;
    }

    if (highlightActive === true) {
        for (var nodeId in allNodes) {
            allNodes[nodeId].color = undefined;
            if (allNodes[nodeId].hiddenLabel !== undefined) {
                allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
                allNodes[nodeId].hiddenLabel = undefined;
            }
        }
        highlightActive = false;
        return;
    }

    var updateArray = [];
    for (nodeID in allNodes) {
        var node = allNodes[nodeID];
        if (node['group'] !== group) {
            node['color'] = 'rgba(200,200,200,0.5)';
        }
        updateArray.push(node);
    }
    nodesDataset.update(updateArray);
    highlightActive = true;
    network.stopSimulation();
}

function fetch_node_info(node_id) {
    var node_label = allNodes[node_id].label;
    $.ajax({
        type: 'GET',
        url: '/doc-lookup',
        data: {
            'cluster_id': node_label
        },
        success: function (data) {
            console.log(data);
            if (data.hasOwnProperty('error_message')) {
                $('#nodeInfo').html(data['error_message']);
                return;
            }
            renderjson.set_icons('++', '--');
            renderjson.set_show_to_level(2);
            $('#nodeInfo').empty();
            for (var key in data) {
                if (!data.hasOwnProperty(key)) {
                    continue;
                }
                $('#nodeInfo').append(renderjson(data[key]));
            }

            $('#nodeProps').html('Degree: ' + network.getConnectedNodes(node_id).length);
        }
    });
}

function remapNodeSizes(nodes) {
    var old_max = Number.MIN_SAFE_INTEGER,
        old_min = Number.MAX_SAFE_INTEGER;

    for (nodeID in nodes) {
        var node = nodes[nodeID];
        if (node['value'] >= old_max) {
            old_max = node['value'];
        }
        if (node['value'] <= old_min) {
            old_min = node['value'];
        }
    }

    var new_max = MAX_NODE_SIZE;
    var new_min = MIN_NODE_SIZE;

    var scaleFactor = (Math.round(0.80 * new_max) - new_min) / (old_max - old_min);
    var updateArray = [];
    for (nodeID in nodes) {
        var node = nodes[nodeID];
        if (node['shape'] === 'star') {
            node['value'] = new_max;
        } else {
            node['value'] = new_min + (scaleFactor * (node['value'] - old_min));
        }
        updateArray.push(node);
    }
    return updateArray;

}

/*
code source:
http://visjs.org/examples/network/exampleApplications/neighbourhoodHighlight.html
*/
function neighbourhoodHighlight(params) {
    // if something is selected:
    if (params.nodes.length > 0) {
        highlightActive = true;
        var i, j;
        var selectedNode = params.nodes[0];
        var degrees = 2;

        // mark all nodes as hard to read.
        for (var nodeId in allNodes) {
            allNodes[nodeId].color = 'rgba(200,200,200,0.5)';
            if (allNodes[nodeId].hiddenLabel === undefined) {
                allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
                allNodes[nodeId].label = undefined;
            }
        }
        var connectedNodes = network.getConnectedNodes(selectedNode);
        var allConnectedNodes = [];

        // get the second degree nodes
        for (i = 1; i < degrees; i++) {
            for (j = 0; j < connectedNodes.length; j++) {
                allConnectedNodes = allConnectedNodes.concat(network.getConnectedNodes(connectedNodes[j]));
            }
        }

        // all second degree nodes get a different color and their label back
        for (i = 0; i < allConnectedNodes.length; i++) {
            allNodes[allConnectedNodes[i]].color = 'rgba(150,150,150,0.75)';
            if (allNodes[allConnectedNodes[i]].hiddenLabel !== undefined) {
                allNodes[allConnectedNodes[i]].label = allNodes[allConnectedNodes[i]].hiddenLabel;
                allNodes[allConnectedNodes[i]].hiddenLabel = undefined;
            }
        }

        // all first degree nodes get their own color and their label back
        for (i = 0; i < connectedNodes.length; i++) {
            allNodes[connectedNodes[i]].color = undefined;
            if (allNodes[connectedNodes[i]].hiddenLabel !== undefined) {
                allNodes[connectedNodes[i]].label = allNodes[connectedNodes[i]].hiddenLabel;
                allNodes[connectedNodes[i]].hiddenLabel = undefined;
            }
        }

        // the main node gets its own color and its label back.
        allNodes[selectedNode].color = undefined;
        if (allNodes[selectedNode].hiddenLabel !== undefined) {
            allNodes[selectedNode].label = allNodes[selectedNode].hiddenLabel;
            allNodes[selectedNode].hiddenLabel = undefined;
        }
    } else if (highlightActive === true) {
        // reset all nodes
        for (var nodeId in allNodes) {
            allNodes[nodeId].color = undefined;
            if (allNodes[nodeId].hiddenLabel !== undefined) {
                allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
                allNodes[nodeId].hiddenLabel = undefined;
            }
        }
        highlightActive = false
    }

    // transform the object into an array
    var updateArray = [];
    for (nodeId in allNodes) {
        if (allNodes.hasOwnProperty(nodeId)) {
            updateArray.push(allNodes[nodeId]);
        }
    }
    nodesDataset.update(updateArray);
}

/*
TODO: Implementation not finished

code source: http://visjs.org/examples/network/other/animationShowcase.html
*/
function focusRandom() {
    updateValues();

    var nodeId = Math.floor(Math.random() * amountOfNodes);
    var options = {
        // position: {x:positionx,y:positiony}, // this is not relevant when focusing on nodes
        scale: scale,
        offset: {
            x: offsetx,
            y: offsety
        },
        animation: {
            duration: duration,
            easingFunction: easingFunction
        }
    };
    statusUpdateSpan.innerHTML = 'Focusing on node: ' + nodeId;
    finishMessage = 'Node: ' + nodeId + ' in focus.';
    network.focus(nodeId, options);
}

var network;
var allNodes, allEdges;
var highlightActive = false;

function redrawAll(container='networkCanvas') {

    var container = document.getElementById(container);
    var options = {
        nodes: {
            shape: 'dot',
            scaling: {
                min: 10,
                max: 30,
                label: {
                    min: 8,
                    max: 30,
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
                min: 0.1,
                max: 5
            },
            width: 1.0,
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
            hideEdgesOnDrag: true
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
    var data = {
        nodes: nodesDataset,
        edges: edgesDataset
    } // Note: data is coming from ./datasources/WorldCup2014.js

    network = new vis.Network(container, data, options);

    // get a JSON object
    allNodes = nodesDataset.get({
        returnType: "Object"
    });

    allEdges = edgesDataset.get({
        returnType: "Object"
    });

    network.on('click', neighbourhoodHighlight);
    network.on('doubleClick', resolveDoubleClick);
}


function resolveDoubleClick(params) {
    console.log(params.nodes);
    if (params.nodes.length == 0) {
        return;
    }
    var node_id = String(params.nodes[0]);
    fetch_node_info(node_id);
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

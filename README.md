# Region-Graph-Exploration

A multi-part platform for decomposing, exploring, and visualizing graphs derived from relationships between sets.

## Getting Started

### Prerequisites

* [python2.7](https://www.python.org/download/releases/2.7/)
* [graph-tool](https://graph-tool.skewed.de/)
* [MongoDB](https://www.mongodb.com/)
* Linux OS (Mac OS may work with some tweaking, but really comes down to graph-tool)

### Installing

While some packages like `graph-tool` require special installation instructions, other package dependencies will generally be defined in `requirements.txt`. To install these dependencies, run the following:

```
sudo pip install requirements.txt
```

Using a virtualenv is highly recommended.

## Background

### Algorithms

TODO: When the time is right, populate this with appropriate background info including set intersections, regions, graph peeling, etc.

### Hierarchy Tree

The hierarchical partitioning tree is the primary means by which users will navigate an input graph *G* with vertex set *V* and edge set *E*. A hierarchical partitioning tree, *T*, is a data structure meant to repeatedly break apart, or decompose, a large graph into small pieaces. Each node on the tree represents a subset of edges and a subset of vertices of the entire graph. The union of the vertex lists and edge lists at any depth of the tree is equivalent to *V* and *E*, respectively (most of the time... more on this later).  

Hierarchical partitioning cycles through several partitioning methods, in order. Currently, the rotation is as follows:
* Peel 1 (k-core 1) [V, E]
* Connected Components [V, E]
* Biconnected Components [E]
* Edge Peeling [E]

The letters in brackets denote which set -- vertex, edge, or both -- is being partitioned. The resulting subsets and relevant metadata are appropriately appended as nodes to the hierarchy tree. There are cases where vertices or edges can, and will, repeat. For example, when a (sub)graph is partitioned using biconnected components, a vertex may belong to multiple biconnected components, but an edge can only belong to a single biconnected component. As such, a vertex may appear in multiple children nodes on the tree of a node being partitioned into biconnected components.  

**TODO**: A seperate repository may be created to host code relating to the hierarchical partitioning tree. A more thorough and mathematical discussion can be hosted there in the future.

## Running the tests

There are currently no build tests for this project. We choose to live life on the edge, but you can help change that.

## Running Locally

Run all scripts and localhost servers from the root directory. For example:

```
python scripts/create_regions.py arg1 arg2 ...
```

Be sure to make `run.py` executable. You can do this with:

```
chmod +x run.py
```

Also check the shebang in `run.py` and make sure it aligns with your python installation directory.

## Deployment

Any web server compatible with Python's Flask microframework will be okay for deployment to a prod server (Apache will do the trick). Here are a few resources to help you get started (some modifications to wsgi.py or run.py may be necessary, of course):  
* [Running a Flask application under the Apache WSGI module](https://www.jakowicz.com/flask-apache-wsgi/)
* [How To Deploy a Flask Application on an Ubuntu VPS ](https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps)

<!-- 
## Contributing

Have a look at [CONTRIBUTING.md](Link to CONTRIBUTING.md)
-->

<!--
## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 
-->

## Known Bugs

**TODO**

## Relevant Project Repositories

[Net Clustering](https://github.com/KirtimanS/Net-Clustering)

## Authors

* **Parth Parikh** - *05/2017 - 08/2017* - [prparikh02](https://github.com/prparikh02)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

<!--
## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
-->

## Acknowledgments

* [Source for this README's initial formatting](https://gist.github.com/PurpleBooth/109311bb0361f32d87a2)

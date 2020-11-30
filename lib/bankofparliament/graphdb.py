"""
Module for graphdb related tasks
"""
# -*- coding: utf-8 -*-

# sys libs

# third party libs
from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError

# local libs
from .constants import NEO4J_URL
from .utils import read_csv_as_dataframe


class GraphDB:
    """Generates neo4j database"""

    LIMIT = -1

    def __init__(self, host, port, user, password, entities, relationships, logger):
        """Initialise the neo4j graphdb class"""
        self.logger = logger
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.entities = entities
        self.relationships = relationships
        self.logger = logger

        graph = self.get_graphdb()
        self.session = graph.session()

    def execute(self):
        """Execute"""
        self.delete_all_nodes_and_relationships()

        entities = read_csv_as_dataframe(self.entities, null_replace="N/A")
        relationships = read_csv_as_dataframe(self.relationships, null_replace="N/A")

        for (_index, row) in relationships[: self.LIMIT].iterrows():

            source, target = None, None
            _source = row["source"]
            _target = row["target"]

            source_filter = entities["name"] == _source
            source_match = entities.loc[source_filter]
            if len(source_match):
                source = source_match.to_dict(orient="records")[0]
                del source["Unnamed: 0"]

            target_filter = entities["name"] == _target
            target_match = entities.loc[target_filter]
            if len(target_match):
                target = target_match.to_dict(orient="records")[0]
                del target["Unnamed: 0"]

            if source and target:
                source_node = self.create_node(source)
                target_node = self.create_node(target)

                relationship = row.to_dict()
                del relationship["source"]
                del relationship["target"]
                del relationship["Unnamed: 0"]
                del relationship["text"]

                self.create_relationship(source_node, target_node, relationship)

    def get_graphdb(self):
        """Get a neo4j graph object"""
        self.logger.info("Connecting to Neo4J")
        url = NEO4J_URL.format(self.host, self.port)
        graph = GraphDatabase.driver(url, auth=(self.user, self.password))
        return graph

    def delete_all_nodes_and_relationships(self):
        """Clean existing db of nodes and relationships"""
        self.logger.info("Cleaning graphdb")
        self.session.run("MATCH (a) DETACH DELETE a")

    def create_node(self, node):
        """Create neo4j node"""
        self.logger.debug("Creating graphdb node: {}".format(node["name"]))

        existing_node = self.get_node(node)
        if not existing_node:
            node_type = node["entity_type"]
            del node["entity_type"]
            try:
                cypher = "CREATE (n:{} {}) RETURN n, labels(n)".format(
                    node_type, self.cypher_arguments_from_dict(node)
                )
                self.logger.debug("Cypher: {}".format(cypher))
                result = self.session.run(cypher)
                data = result.data()
                return data[0]
            except CypherSyntaxError as error:
                self.logger.error("Failed to create node: {}".format(error))
                return None

            data = result.data()
            return data[0]
        return existing_node

    def get_node(self, node):
        """Query for existing node"""
        self.logger.debug("Getting graphdb node: {}".format(node["name"]))
        try:
            cypher = "MATCH (n:{} {}) RETURN n, labels(n)".format(
                node["entity_type"],
                self.cypher_arguments_from_dict({"name": node["name"]}),
            )
            self.logger.debug("Cypher: {}".format(cypher))
            result = self.session.run(cypher)
        except CypherSyntaxError as error:
            self.logger.error("Failed to query for node: {}".format(error))
            return None

        data = result.data()
        if len(data) > 0:
            return data[0]
        return None

    def create_relationship(self, source, target, relationship):
        """Create neo4j relationship between two nodes"""
        self.logger.info(
            "Creating graphdb relationship: {} > {}".format(
                source["n"]["name"], target["n"]["name"]
            )
        )

        source_name = source["n"]["name"]
        target_name = target["n"]["name"]
        source_labels = source["labels(n)"][0]
        target_labels = target["labels(n)"][0]

        relationship_type = relationship["relationship_type"]
        relationship_data = self.cypher_arguments_from_dict(relationship)

        try:
            cypher = "MATCH (a:{}),(b:{})".format(source_labels, target_labels)
            cypher += 'WHERE a.name = "{}" AND b.name = "{}"'.format(
                source_name, target_name
            )
            cypher += "CREATE (a)-[r:{} {}]->(b)".format(
                relationship_type, relationship_data
            )
            cypher += "RETURN r"

            self.logger.debug("Cypher: {}".format(cypher))
            result = self.session.run(cypher)
        except CypherSyntaxError as error:
            self.logger.error("Failed to create relationship: {}".format(error))
            return None

        data = result.data()
        return data[0]

    def cypher_arguments_from_dict(self, data):
        """Convert dictionary to cypher query arguments"""
        node_string = ""
        for key, value in data.items():
            if key not in ["relationship_type", "entity_type"]:
                node_string += '{}: "{}", '.format(key, value)
        return "{" + node_string[:-2] + "}"

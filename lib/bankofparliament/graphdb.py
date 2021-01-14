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
from .text import eval_string_as_list


class GraphDB:
    """Generates neo4j database"""

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

        entities = read_csv_as_dataframe(self.entities)
        relationships = read_csv_as_dataframe(self.relationships)

        for (_index, row) in relationships.iterrows():
            source, target = None, None
            _source = row["source"]
            _target = row["target"]
            _amount = row["amount"]
            _recurring = row["recurring"]

            source_filter = entities["name"].str.lower() == _source.lower()
            source_match = entities.loc[source_filter]
            if len(source_match):
                source = source_match.to_dict(orient="records")[0]

            target_filter = entities["name"].str.lower() == _target.lower()
            target_match = entities.loc[target_filter]
            if len(target_match):
                target = target_match.to_dict(orient="records")[0]

            if source and target and _recurring != "N/A":
                source_node = self.create_node(source)
                target_node = self.create_node(target)

                relationship = row.to_dict()
                del relationship["source"]
                del relationship["target"]
                del relationship["recurring"]

                try:
                    texts = eval_string_as_list(relationship["text"])
                    text = "</br>".join(texts)
                except:
                    text = relationship["text"]
                text = text.replace('"', "'")
                relationship["text"] = text

                if relationship["amount"] == "N/A":
                    relationship["amount"] = 0
                else:
                    relationship["amount"] = int(float(relationship["amount"]))

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

            if node_type in ["politician", "advisor"]:
                node_type = ":".join([node_type, "person"])

            elif node_type not in [
                "person",
                "politician",
                "advisor",
                "property",
                "profession",
            ]:
                node_type = ":".join([node_type, "organisation"])

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
            cypher = "MATCH (a:{}),(b:{}) ".format(source_labels, target_labels)
            cypher += 'WHERE a.name = "{}" AND b.name = "{}" '.format(
                source_name, target_name
            )
            cypher += "CREATE (a)-[r:{} {}]->(b) ".format(
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
            if key not in ["relationship_type", "entity_type", "aliases", "resolved"]:
                if key == "amount":
                    node_string += "{}: {}, ".format(key, value)
                else:
                    node_string += '{}: "{}", '.format(key, value)
        return "{" + node_string[:-2] + "}"

"""
Module for relationships
"""
# -*- coding: utf-8 -*-
from .text import eval_string_as_list

class Relationship:
    def __init__(self, id, relationship, entities):
        """
        Relationship - pandas DataFrame
        """
        self.id = id
        self.relationship = relationship
        self.entities = entities

        self._relationship_type = relationship["relationship_type"]
        self._source = relationship["source"]
        self._target = relationship["target"]
        self._date = None
        self._amount = None

    @property
    def source(self):
        """"""
        return self._source

    @property
    def target(self):
        """"""
        return self._target

    @property
    def date(self):
        """"""
        return self._date

    @property
    def amount(self):
        """"""
        return self._amount

    @property
    def relationship_type(self):
        """"""
        return self._relationship_type

    def _is_known_entity(self, entity_name, entity_type=None):
        """"""
        if entity_type:
            filt = (self.entities["name"].str.lower() == entity_name.lower()) & (
                self.entities["entity_type"].str.lower() == entity_type.lower()
                )
            entity = self.entities.loc[filt]
            if len(entity):
                return True
        return False

    def __repr__(self):
        """"""
        return "[{:05d}] [{}] -- [{}] --> [{}]".format(self.id, self.source, self.relationship_type, self.target)

class TextRelationship(Relationship):
    def evaluate(self):
        """"""
        self.data = eval_string_as_list(self.relationship["text"])[0]

    def get_known_entities_in_text(self, entity_type=None):
        """"""


    def clean(self):
        """"""
        entities = self.get_known_entities_in_text()


class CompoundRelationship(Relationship):
    def evaluate(self):
        """"""
        """Find key/value info from list of texts"""
        data = dict.fromkeys(["name", "amount", "status", "address", "date", "destination", "purpose"], "")

        for line in eval_string_as_list(self.relationship["text"]):
            if ":" in line:
                splits = line.split(":")
                key = splits[0].strip()
                value = splits[-1].strip()

                if "name" in key.lower():
                    data["name"] = value

                elif "amount" in key.lower() or "value" in key.lower():
                    data["amount"] = value

                elif "status" in key.lower():
                    data["status"] = value

                elif "address" in key.lower():
                    data["address"] = value

                elif "destination" in key.lower():
                    data["destination"] = value

                elif "purpose" in key.lower():
                    data["purpose"] = value

            if "registered" in line.lower():
                data["date"] = line

        self.data = data

class Membership(TextRelationship):
    pass
class SignificationControl(TextRelationship):
    pass
class Directorship(TextRelationship):
    pass
class Relation(TextRelationship):
    pass
class PropertyOwner(TextRelationship):
    pass
class Sponsorship(TextRelationship):
    pass
class Shareholder(TextRelationship):
    pass
class Donation(CompoundRelationship):
    pass
class Gift(CompoundRelationship):
    pass
class Visit(CompoundRelationship):
    pass
class Employment(TextRelationship):
    pass
class Miscellaneous(TextRelationship):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def get_relationship(id, relationship, entities):
    """"""
    relationship_type = relationship["relationship_type"]

    if relationship_type == "member_of":
        return Membership(id, relationship, entities)

    elif relationship_type == "significant_control_of":
        return SignificationControl(id, relationship, entities)

    elif relationship_type == "director_of":
        return Directorship(id, relationship, entities)

    elif relationship_type == "related_to":
        return Relation(id, relationship, entities)

    elif relationship_type == "owner_of":
        return PropertyOwner(id, relationship, entities)

    elif relationship_type == "sponsored_by":
        return Sponsorship(id, relationship, entities)

    elif relationship_type == "shareholder_of":
        return Shareholder(id, relationship, entities)

    elif relationship_type == "donations_from":
        return Donation(id, relationship, entities)

    elif relationship_type == "gifts_from":
        return Gift(id, relationship, entities)

    elif relationship_type == "visited":
        return Visit(id, relationship, entities)

    elif relationship_type == "employed_by":
        return Employment(id, relationship, entities)

    elif relationship_type == "miscellaneous":
        return Miscellaneous(id, relationship, entities)

    return None
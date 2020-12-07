"""
Module for relationships
"""
# -*- coding: utf-8 -*-
from ..text import eval_string_as_list

class BaseRelationship:
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

class TextRelationship(BaseRelationship):
    def evaluate(self):
        """"""
        self.data = eval_string_as_list(self.relationship["text"])[0]

class CompoundRelationship(BaseRelationship):
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

def get_relationship(id, relationship, entities):
    """"""
    relationship_type = relationship["relationship_type"]

    if relationship_type == "member_of":
        from .membership import Membership
        return Membership(id, relationship, entities)

    elif relationship_type == "significant_control_of":
        from .significant import SignificationControl
        return SignificationControl(id, relationship, entities)

    elif relationship_type == "director_of":
        from .director import Directorship
        return Directorship(id, relationship, entities)

    elif relationship_type == "related_to":
        from .relation import Relation
        return Relation(id, relationship, entities)

    elif relationship_type == "owner_of":
        from .property import PropertyOwner
        return PropertyOwner(id, relationship, entities)

    elif relationship_type == "sponsored_by":
        from .sponsor import Sponsorship
        return Sponsorship(id, relationship, entities)

    elif relationship_type == "shareholder_of":
        from .shareholder import Shareholder
        return Shareholder(id, relationship, entities)

    elif relationship_type == "donations_from":
        from .donation import Donation
        return Donation(id, relationship, entities)

    elif relationship_type == "gifts_from":
        from .gift import Gift
        return Gift(id, relationship, entities)

    elif relationship_type == "visited":
        from .visit import Visit
        return Visit(id, relationship, entities)

    elif relationship_type == "employed_by":
        from .employment import Employment
        return Employment(id, relationship, entities)

    elif relationship_type == "miscellaneous":
        from .miscellaneous import Miscellaneous
        return Miscellaneous(id, relationship, entities)

    return None
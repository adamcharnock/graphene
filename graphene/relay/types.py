import inspect
import warnings
from collections import Iterable
from functools import wraps

import six
from graphql_relay.connection.arrayconnection import connection_from_list
from graphql_relay.node.node import to_global_id

from ..core.classtypes import InputObjectType, Interface, Mutation, ObjectType
from ..core.classtypes.interface import InterfaceMeta
from ..core.classtypes.mutation import MutationMeta
from ..core.types import Boolean, Field, List, String
from ..core.types.argument import ArgumentsGroup
from ..core.types.definitions import NonNull
from ..utils import memoize
from .fields import GlobalIDField


class PageInfo(ObjectType):
    has_next_page = Boolean(
        required=True,
        description='When paginating forwards, are there more items?')
    has_previous_page = Boolean(
        required=True,
        description='When paginating backwards, are there more items?')
    start_cursor = String(
        description='When paginating backwards, the cursor to continue.')
    end_cursor = String(
        description='When paginating forwards, the cursor to continue.')


class Edge(ObjectType):
    '''An edge in a connection.'''
    cursor = String(
        required=True, description='A cursor for use in pagination')

    @classmethod
    @memoize
    def for_node(cls, node):
        from graphene.relay.utils import is_node
        assert is_node(node), 'ObjectTypes in a edge have to be Nodes'
        node_field = Field(node, description='The item at the end of the edge')
        return type(
            '%s%s' % (node._meta.type_name, cls._meta.type_name),
            (cls,),
            {'node_type': node, 'node': node_field})


class Connection(ObjectType):
    '''A connection to a list of items.'''
    class Meta:
        type_name = 'DefaultConnection'

    page_info = Field(PageInfo, required=True,
                      description='The Information to aid in pagination')

    _connection_data = None

    @classmethod
    @memoize
    def for_node(cls, node, edge_type=None):
        from graphene.relay.utils import is_node
        edge_type = edge_type or Edge.for_node(node)
        assert is_node(node), 'ObjectTypes in a connection have to be Nodes'
        edges = List(edge_type, description='Information to aid in pagination.')
        return type(
            '%s%s' % (node._meta.type_name, cls._meta.type_name),
            (cls,),
            {'edge_type': edge_type, 'edges': edges})

    @classmethod
    def from_list(cls, iterable, args, info):
        assert isinstance(
            iterable, Iterable), 'Resolved value from the connection field have to be iterable'
        connection = connection_from_list(
            iterable, args, connection_type=cls,
            edge_type=cls.edge_type, pageinfo_type=PageInfo)
        connection.set_connection_data(iterable)
        return connection

    def set_connection_data(self, data):
        self._connection_data = data

    def get_connection_data(self):
        return self._connection_data


class NodeMeta(InterfaceMeta):

    def construct_get_node(cls):
        get_node = getattr(cls, 'get_node', None)
        assert get_node, 'get_node classmethod not found in %s Node' % cls
        assert callable(get_node), 'get_node have to be callable'
        args = 3
        if isinstance(get_node, staticmethod):
            args -= 1

        get_node_num_args = len(inspect.getargspec(get_node).args)
        if get_node_num_args < args:
            warnings.warn("get_node will receive also the info arg"
                          " in future versions of graphene".format(cls.__name__),
                          FutureWarning)

            @staticmethod
            @wraps(get_node)
            def wrapped_node(*node_args):
                if len(node_args) < args:
                    node_args += (None, )
                return get_node(*node_args[:-1])

            setattr(cls, 'get_node', wrapped_node)

    def construct(cls, *args, **kwargs):
        cls = super(NodeMeta, cls).construct(*args, **kwargs)
        if not cls._meta.abstract:
            cls.construct_get_node()
        return cls


class Node(six.with_metaclass(NodeMeta, Interface)):
    '''An object with an ID'''
    id = GlobalIDField()

    class Meta:
        abstract = True

    def to_global_id(self):
        type_name = self._meta.type_name
        return to_global_id(type_name, self.id)

    connection_type = Connection
    edge_type = Edge

    @classmethod
    def get_connection_type(cls):
        return cls.connection_type

    @classmethod
    def get_edge_type(cls):
        return cls.edge_type


class MutationInputType(InputObjectType):
    client_mutation_id = String(required=True)


class RelayMutationMeta(MutationMeta):

    def construct(cls, *args, **kwargs):
        cls = super(RelayMutationMeta, cls).construct(*args, **kwargs)
        if not cls._meta.abstract:
            assert hasattr(
                cls, 'mutate_and_get_payload'), 'You have to implement mutate_and_get_payload'
        return cls

    def construct_arguments(cls, items):
        new_input_type = type('{}Input'.format(
            cls._meta.type_name), (MutationInputType, ), items)
        cls.add_to_class('input_type', new_input_type)
        return ArgumentsGroup(input=NonNull(new_input_type))


class ClientIDMutation(six.with_metaclass(RelayMutationMeta, Mutation)):
    client_mutation_id = String(required=True)

    class Meta:
        abstract = True

    @classmethod
    def mutate(cls, instance, args, info):
        input = args.get('input')
        payload = cls.mutate_and_get_payload(input, info)
        client_mutation_id = input.get('client_mutation_id')
        setattr(payload, 'client_mutation_id', client_mutation_id)
        return payload

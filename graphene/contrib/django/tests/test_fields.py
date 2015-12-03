from graphene.contrib.django import DjangoFilterConnectionField, DjangoNode
from graphene.contrib.django.tests.filters import ArticleFilter, PetFilter
from graphene.contrib.django.tests.models import Article, Pet


class ArticleNode(DjangoNode):
    class Meta:
        model = Article


class PetNode(DjangoNode):
    class Meta:
        model = Pet


def assert_arguments(field, *arguments):
    ignore = ('after', 'before', 'first', 'last', 'o')
    actual = [
        name
        for name in field.arguments.arguments.keys()
        if name not in ignore and not name.startswith('_')
    ]
    assert set(arguments) == set(actual), \
        'Expected arguments ({}) did not match actual ({])'.format(
            arguments,
            actual
        )


def assert_orderable(field):
    assert 'o' in field.arguments.arguments.keys(), \
        'Field cannot be ordered'


def assert_not_orderable(field):
    assert 'o' in field.arguments.arguments.keys(), \
        'Field cannot be ordered'


def test_filter_explicit_filterset_arguments():
    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleFilter)
    assert_arguments(field,
                     'headline', 'headlineIcontains',
                     'pubDate', 'pubDateGt', 'pubDateLt',
                     'reporter',
                     )


def test_filter_shortcut_filterset_arguments_list():
    field = DjangoFilterConnectionField(ArticleNode, fields=['pub_date', 'reporter'])
    assert_arguments(field,
                     'pubDate',
                     'reporter',
                     )


def test_filter_shortcut_filterset_arguments_dict():
    field = DjangoFilterConnectionField(ArticleNode, fields={
            'headline': ['exact', 'icontains'],
            'reporter': ['exact'],
        })
    assert_arguments(field,
                     'headline', 'headlineIcontains',
                     'reporter',
                     )


def test_filter_explicit_filterset_orderable():
    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleFilter)
    assert_orderable(field)


def test_filter_shortcut_filterset_orderable_true():
    field = DjangoFilterConnectionField(ArticleNode, order_by=True)
    assert_orderable(field)


def test_filter_shortcut_filterset_orderable_headline():
    field = DjangoFilterConnectionField(ArticleNode, order_by=['headline'])
    assert_orderable(field)


def test_filter_explicit_filterset_not_orderable():
    field = DjangoFilterConnectionField(PetNode, filterset_class=PetFilter)
    assert_not_orderable(field)


def test_filter_shortcut_filterset_extra_meta():
    field = DjangoFilterConnectionField(ArticleNode, extra_filter_meta={
        'ordering': True
    })
    assert_orderable(field)
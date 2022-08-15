from .models import OrganisationNode, Organisation
from uuid import UUID


def get_all_children_nodes(parent_id: UUID) -> list:
    """
    This function basically returns all the direct children of a parent node

    param: uuid
    returns: List
    """
    children = list(
        OrganisationNode.objects.filter(parent=parent_id).values_list("id", flat=True)
    )
    return children


def get_leaf_node_ids(organisation: Organisation) -> list:
    """
    This function basically returns all the leaf nodes in an Organisation(Organisation being the root node)
    """
    querysets = OrganisationNode.objects.filter(organisation=organisation)
    leaf_node_ids = []
    for queryset in querysets:
        children = get_all_children_nodes(queryset.id)
        if not children:
            leaf_node_ids.append(queryset.id)
    return leaf_node_ids


def is_org_level_sequential(validated_levels: list, org_levels: list) -> bool:
    """Function to validate levels received from the frontend forms against the organisation levels structure."""
    assert isinstance(
        org_levels, list
    ), "Organisation Levels expects a List as it's parameter."

    if len(validated_levels) > len(org_levels):
        return False

    for index, _ in enumerate(sorted(validated_levels)):
        if validated_levels[index] == org_levels[index]:
            continue
        else:
            return False
    return True


def get_org_levels_sublevels(level_id: (int, str)):
    """A Function to get the sublevels of a Level."""
    assert str(level_id).isnumeric(), "Level id must be an integer"

    level_id = int(level_id)
    level_objs = OrganisationNode.objects.filter(
        parent__level=level_id, level=level_id + 1
    )
    return level_objs

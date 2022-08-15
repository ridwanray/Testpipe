# DECORATORS FOR HRMS ORGANISATION MODEL

from django.db.models import Q
from django.http import Http404
from rest_framework import serializers

from employee.models import Employee
from organisation.models import Organisation


def is_organisation_active(func):
    """
    Checks if the organisation status is active.
    """

    def wrapper(request, *args, **kwargs):
        if request.user.organisation.status == "ACTIVE":
            return func(request, *args, **kwargs)
        else:
            return serializers.ValidationError(
                {"error": f"Organisation is not active."}
            )

    return wrapper


@is_organisation_active
def is_organisation_user(func):
    """
    This function requires the wrapper function to accept active and authenticated users.
    :rtype: wrapper function
    :param func:
    :return:
    """

    def wrapper(request, *args, **kwargs):
        # Check if the user is part of the Organisation.
        if (
            request.user.organisation
            and Organisation.objects.filter(admin=request.user).exists()
        ):
            return func(request, *args, **kwargs)
        else:
            return serializers.ValidationError(
                {"error": f"User has no record in {request.user.organisation}."}
            )

    return wrapper


@is_organisation_user
def is_organisation_superadmin(func):
    """
    This function requires the wrapper function to accept employees of the organisation.
    :rtype: function
    :param func: callable method
    :return: wrapper
    """

    def wrapper(request, *args, **kwargs):
        # Check if the user is part of the Organisation and that user is a SUPERADMIN.
        if request.user.roles == "SUPERADMIN":
            return func(request, *args, **kwargs)
        else:
            return serializers.ValidationError(
                {"error": "SUPERADMIN cannot be verified. Is SUPERADMIN valid?"}
            )

    return wrapper


@is_organisation_user
def is_organisation_hradmin(func):
    """
    This function requires the wrapper function to accept hradmin of the organisation.
    :rtype: function
    :param func: callable method
    :return: wrapper
    """

    def wrapper(request, *args, **kwargs):
        # Check if the user is part of the Organisation and that user is a HRADMIN.
        if request.user.roles == "HRADMIN":
            return func(request, *args, **kwargs)
        else:
            return serializers.ValidationError(
                {"error": "HRADMIN cannot be verified. Is HRADMIN valid?"}
            )

    return wrapper


@is_organisation_user
def is_organisation_executive(func):
    """
    This function requires the wrapper function to accept executive of the organisation.
    :rtype: function
    :param func: callable method
    :return: wrapper
    """

    def wrapper(request, *args, **kwargs):
        # Check if the user is part of the Organisation and that user is a EXECUTIVE.
        if request.user.roles == "EXECUTIVE":
            return func(request, *args, **kwargs)
        else:
            return serializers.ValidationError(
                {"error": "EXECUTIVE cannot be verified. Is EXECUTIVE valid?"}
            )

    return wrapper


@is_organisation_user
def is_organisation_employee(func):
    """
    This function requires the wrapper function to accept employees of the organisation.
    :rtype: function
    :param func: callable method
    :return: wrapper
    """

    def wrapper(request, *args, **kwargs):
        # Check if the user is part of the Organisation and that user is an employee.
        valid_employee = Employee.objects.filter(
            Q(user=request.user) & ~Q(invitation_status="PENDING")
        ).exists()
        if request.user.roles == "EMPLOYEE" and valid_employee:
            return func(request, *args, **kwargs)
        else:
            return serializers.ValidationError(
                {"error": "Employee cannot be verified. Is Employee valid?"}
            )

    return wrapper

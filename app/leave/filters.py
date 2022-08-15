# from django.db.models import Q
# from django_filters.rest_framework import FilterSet
# import django_filters as filters
#
# from .models import LeaveRequest
#
#
# class LeaveRequestFilter(FilterSet):
#     search = filters.CharFilter(method='filter_search')
#     ordering = filters.OrderingFilter(fields=('type', 'status'))
#
#     @staticmethod
#     def filter_search(queryset, name, value):
#         return queryset.filter(Q(note__icontains=value) | Q(type__title__icontains=value))
#
#     class Meta:
#         model = LeaveRequest
#         fields = ('type', 'status')

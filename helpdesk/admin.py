# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from copy import deepcopy


from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from mezzanine.core.admin import TabularDynamicInlineAdmin

from .models import Category, Tipology, Attachment, Ticket, HelpdeskUser
from .forms import TicketAdminForm


class TipologyInline(TabularDynamicInlineAdmin):
    extra = 3
    model = Tipology


class AttachmentInline(TabularDynamicInlineAdmin):
    extra = 1
    model = Attachment


class CategoryAdmin(admin.ModelAdmin):
    inlines = [TipologyInline]
    list_display = ['title', 'admin_tipologies']
    search_fields = ['title']


class TipologyAdmin(admin.ModelAdmin):
    list_display = ['title', 'admin_category', 'admin_sites']
    list_filter = ['category']
    search_fields = ['title', 'category__title']


class TicketAdmin(admin.ModelAdmin):
    filter_horizontal = ('tipologies', 'related_tickets')
    form = TicketAdminForm
    inlines = [AttachmentInline]
    list_display = ['pk', 'content', 'status', ]
    list_filter = ['priority', 'status', 'tipologies']
    list_per_page = 25
    list_select_related = True
    radio_fields = {'priority': admin.HORIZONTAL}
    search_fields = ['content', 'user__username', 'user__first_name',
                     'user__last_name', 'requester__username',
                     'requester__first_name', 'requester__last_name',
                     'tipologies__title']

    fieldsets = (
        (None, {
            "fields": ["tipologies", "priority", "content"],
        }),
        (_("Related tickets"), {
            "classes": ("collapse-closed",),
            "fields": ("related_tickets",)
        }),
    )

    def get_request_helpdeskuser(self, request):
        return HelpdeskUser.objects.get(pk=request.user.pk)

    def get_fieldsets(self, request, obj=None):
        """
        Return default fieldsets if request.user is a requester.
        Otherwise request.user is a operator, an admin or superuser, append
        'requester' field to fieldsets.
        """
        user = self.get_request_helpdeskuser(request)
        fieldset = super(TicketAdmin, self).get_fieldsets(request, obj=obj)
        if user.is_superuser or user.is_operator() or user.is_admin():
            fieldset = deepcopy(fieldset)
            fieldset[0][1]['fields'].append('requester')
        return fieldset

    def get_readonly_fields(self, request, obj=None):
        """
        Return a tuple with all fields if request.user is a requester.
        Otherwise return default empty readonly_fields.
        """
        if obj:
            user = self.get_request_helpdeskuser(request)
            if user.is_requester():
                fields = []
                for e in self.fieldsets:
                    fields += e[1]['fields']
                return tuple(fields)
        return super(TicketAdmin, self).get_readonly_fields(request, obj=obj)

    def get_list_filter(self, request):
        """
        Return default list_filter if request.user is a requester. Otherwise
        if request.user is a operator, an admin or superuser, return default
        list_filter with append more fields.
        """
        user = self.get_request_helpdeskuser(request)
        list_filter = super(TicketAdmin, self).get_list_filter(request)
        if user.is_superuser or user.is_operator() or user.is_admin():
            list_filter = list(list_filter) + ['requester', 'assignee']
        return list_filter

    def get_queryset(self, request):
        """
        Return a filtered queryset by user that match with request.user if
        request.user is a requester. Otherwise if request.user is a operator,
        an admin or superuser, queryset returned is not filtered.
        """
        user = self.get_request_helpdeskuser(request)
        # compatibility for django 1.5 where "get_queryset" method is
        # called "queryset" instead
        f_get_queryset = getattr(
            super(TicketAdmin, self), 'get_queryset', None)
        if not f_get_queryset:
            f_get_queryset = getattr(super(TicketAdmin, self), 'queryset')
        qs = f_get_queryset(request)
        if user.is_superuser or user.is_operator() or user.is_admin():
            return qs
        return qs.filter(requester=user)

    def queryset(self, request):
        """
        Compatibility for django 1.5 where "get_queryset" method is
        called "queryset" instead
        """
        return self.get_queryset(request)

    def save_model(self, request, obj, form, change):
        if obj.requester_id is None:
            obj.requester = request.user
        return super(TicketAdmin, self).save_model(request, obj, form, change)


admin.site.register(Category, CategoryAdmin)
admin.site.register(Tipology, TipologyAdmin)
admin.site.register(Ticket, TicketAdmin)

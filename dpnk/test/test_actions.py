# -*- coding: utf-8 -*-

# Author: Petr Dlouhý <petr.dlouhy@auto-mat.cz>
#
# Copyright (C) 2016 o.s. Auto*Mat
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import datetime

from unittest.mock import MagicMock

import createsend

from django.contrib import admin
from django.contrib.messages.api import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

from dpnk import actions, models, util

from model_mommy import mommy


class TestActionsMommy(TestCase):
    """ Tests that are independend of fixtures """
    def setUp(self):
        self.modeladmin = admin.ModelAdmin(models.UserAttendance, "")
        self.factory = RequestFactory()
        self.request = self.factory.get("")
        self.request.subdomain = "testing-campaign"
        self.request.user = mommy.make(
            "auth.User",
            username="test",
            is_staff=True,
            is_superuser=True,
        )
        setattr(self.request, 'session', 'session')
        self.messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', self.messages)

    def test_assign_vouchers(self):
        mommy.make_recipe('dpnk.test.UserAttendanceRecipe')
        queryset = models.UserAttendance.objects.all()
        vouchers = mommy.make(
            "Voucher",
            voucher_type="rekola",
            token="vouchertoken",
            campaign=queryset[0].campaign,
            _quantity=2,
        )
        voucher = vouchers[0]
        self.assertEquals(voucher.user_attendance, None)
        actions.assign_vouchers(self.modeladmin, self.request, queryset)
        voucher.refresh_from_db()
        self.assertNotEquals(voucher.user_attendance.pk, None)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Úspěšně přiřazeno 1 voucherů")

    def test_assign_vouchers_not_enough(self):
        mommy.make_recipe(
            'dpnk.test.UserAttendanceRecipe',
            _quantity=2,
        )
        queryset = models.UserAttendance.objects.all()
        actions.assign_vouchers(self.modeladmin, self.request, queryset)
        voucher = mommy.make(
            "Voucher",
            voucher_type="rekola",
            token="vouchertoken",
            campaign=queryset[0].campaign,
        )
        self.assertEquals(voucher.user_attendance, None)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Není dost volných voucherů")


@override_settings(
    FAKE_DATE=datetime.date(year=2010, month=11, day=20),
)
class TestActions(TestCase):
    fixtures = ['sites', 'campaign', 'auth_user', 'users', 'transactions', 'batches', 'trips', 'test_results_data', 'invoices']

    def setUp(self):
        self.modeladmin = admin.ModelAdmin(models.UserAttendance, "")
        self.factory = RequestFactory()
        self.request = self.factory.get("")
        self.request.subdomain = "testing-campaign"
        self.request.user = models.User.objects.get(username="test")
        setattr(self.request, 'session', 'session')
        self.messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', self.messages)
        call_command('denorm_init')
        util.rebuild_denorm_models(models.Team.objects.filter(pk=1))

    def tearDown(self):
        call_command('denorm_drop')

    def test_approve_am_payment(self):
        models.Payment.objects.get(pk=17).delete()
        util.rebuild_denorm_models(models.UserAttendance.objects.filter(pk=2115))
        queryset = models.UserAttendance.objects.all()
        payment = models.Payment.objects.get(pk=5)
        self.assertEquals(payment.status, 1)
        actions.approve_am_payment(self.modeladmin, self.request, queryset)
        payment = models.Payment.objects.get(pk=5)
        self.assertEquals(payment.status, 99)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Platby potvrzeny")

    def test_update_mailing(self):
        ret_mailing_id = "344ass"
        createsend.Subscriber.add = MagicMock(return_value=ret_mailing_id)
        createsend.Subscriber.get = MagicMock()
        createsend.Subscriber.update = MagicMock()
        queryset = models.UserAttendance.objects.all()
        actions.update_mailing(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(message, "Aktualizace mailing listu byla úspěšne zadána pro 8 uživatelů")

    def test_show_distance(self):
        queryset = models.UserAttendance.objects.all()
        actions.show_distance(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Ujetá vzdálenost: 167.2 Km v 3 jízdách")

    def test_recalculate_results(self):
        util.rebuild_denorm_models(models.Team.objects.filter(pk__in=[2, 3]))
        queryset = models.UserAttendance.objects.all()
        actions.recalculate_results(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Výsledky přepočítány")

    def test_touch_items_user_attendance(self):
        util.rebuild_denorm_models(models.Team.objects.filter(pk__in=[2, 3]))
        queryset = models.UserAttendance.objects.all()
        actions.touch_items(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Obnova 8 denormalizovaných položek byla zadána ke zpracování")

    def test_touch_items_team(self):
        queryset = models.Team.objects.all()
        actions.touch_items(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Obnova 4 denormalizovaných položek byla zadána ke zpracování")

    def test_recalculate_competitions_results(self):
        queryset = models.Competition.objects.all()
        actions.recalculate_competitions_results(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Zadáno přepočítání 11 výsledků")

    def test_normalize_questionnqire_admissions(self):
        queryset = models.Competition.objects.all()
        actions.normalize_questionnqire_admissions(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(str(message), "Úspěšně obnoveno 1 přihlášek podle odpovědí na dotazník")

    def test_remove_mailing_id(self):
        self.assertEquals(models.UserProfile.objects.get(pk=1026).mailing_id, "")
        queryset = models.UserProfile.objects.all()
        actions.remove_mailing_id(self.modeladmin, self.request, queryset)
        self.assertEquals(models.UserProfile.objects.get(pk=1026).mailing_id, None)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(message, "Mailing ID a hash byl úspěšne odebrán 8 profilům")

    def test_show_distance_trips(self):
        queryset = models.Trip.objects.all()
        actions.show_distance_trips(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(message, "Ujetá vzdálenost: 167.2 Km v 5 jízdách")

    def test_update_mailing_coordinator(self):
        queryset = models.CompanyAdmin.objects.all()
        actions.update_mailing_coordinator(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(message, "Úspěšně aktualizován mailing pro 3 koordinátorů")

    def test_mark_invoices_paid(self):
        queryset = models.Invoice.objects.all()
        actions.mark_invoices_paid(self.modeladmin, self.request, queryset)
        message = get_messages(self.request)._queued_messages[0].message
        self.assertEquals(message, "1 faktur označeno jako 'zaplaceno'")

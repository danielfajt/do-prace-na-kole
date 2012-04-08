# -*- coding: utf-8 -*-
# Author: Hynek Hanke <hynek.hanke@auto-mat.cz>
#
# Copyright (C) 2012 o.s. Auto*Mat
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

# Standard library imports
import time, random, httplib, urllib, hashlib
# Django imports
from django import forms, http
from django.shortcuts import render_to_response
# Registration imports
import registration.forms, registration.signals, registration.backends
# Model imports
from models import User, UserProfile, Team, Payment

class RegistrationFormDPNK(registration.forms.RegistrationForm):
    firstname = forms.CharField(
        label="Jméno",
        max_length=30)
    surname = forms.CharField(
        label="Příjmení",
        max_length=30)
    team = forms.ModelChoiceField(
        label="Tým",
        queryset=Team.objects.all())
    team_password = forms.CharField(
        label="Heslo týmu",
        max_length=20)
    sex = forms.ChoiceField(
        label="Pohlaví",
        choices=UserProfile.GENDER)
    language = forms.ChoiceField(
        label="Jazyk",
        choices=UserProfile.LANGUAGE)
    # -- Contacts
    telephone = forms.CharField(
        label="Telefon",
        max_length=30)

    def __init__(self, request=None, *args, **kwargs):
        if request:
            initial = kwargs.get('initial', {})
            if request.GET.get('team_password', None):
                initial['team_password'] = request.GET['team_password']
            if request.GET.get('team', None):
                initial['team'] = request.GET['team']
            kwargs['initial']=initial

        super(RegistrationFormDPNK, self).__init__(*args, **kwargs)
        self.fields.keyOrder = [
            'firstname',
            'surname',
            'team',
            'team_password',
            'sex',
            'language',
            'email',
            'telephone',
            'username',
            'password1',
            'password2'
            ]

    def clean_team_password(self):
        data = self.cleaned_data['team_password']
        if data != 'tajemstvi':
            raise forms.ValidationError("Nesprávné heslo týmu")
        return data

def register(request, backend='registration.backends.simple.SimpleBackend',
             success_url=None, form_class=None,
             disallowed_url='registration_disallowed',
             template_name='registration/registration_form.html',
             extra_context=None):

    backend = registration.backends.get_backend(backend)
    form_class = RegistrationFormDPNK

    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_user = backend.register(request, **form.cleaned_data)
            if success_url is None:
                to, args, kwargs = backend.post_registration_redirect(request, new_user)
                return redirect(to, *args, **kwargs)
            else:
                return redirect(success_url)
    else:
        form = form_class(request)

    return render_to_response(template_name,
                              {'form': form})

def create_profile(user, request, **kwargs):
    from dpnk.models import UserProfile
    UserProfile(user = user,
                team = Team.objects.get(id=request.POST['team']),
                sex = request.POST['sex'],
                language = request.POST['language'],
                telephone = request.POST['telephone'],
                firstname = request.POST['firstname'],
                surname = request.POST['surname']
                ).save()
registration.signals.user_registered.connect(create_profile)

class RegisterTeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = ('city', 'name', 'company')

def register_team(request):
    if request.method == 'POST':
        form = RegisterTeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.password = random.choice([l.strip() for l in open('/home/aplikace/dpnk/slova.txt')])
            form.save()
            return render_to_response('registration/team_password.html', {
                    'team_id': team.id,
                    'team_password': team.password
                    })
    else:
        form = RegisterTeamForm()
    return render_to_response('registration/register_team.html', {
            'form': form,
            })

def payment(request):
    uid = 2 # uid
    order_id = '2-1' #uid
    session_id = "%sJ%d " % (order_id, int(time.time())) # uid
    p = Payment(session_id=session_id,
                user=UserProfile.objects.get(user__id=uid), # uid
                order_id = order_id,
                amount = 200,
                description = "Účastnický poplatek Do práce na kole")
    p.save()
    return render_to_response('registration/payment.html',
                              {
            'firstname': 'Hynek', # firstname
            'surname': 'Hanke', # surname
            'email': 'hanke@brailcom.org', # email
            'amount': p.amount,
            'amount_hal': p.amount * 100, # v halerich
            'description' : p.description,
            'order_id' : p.order_id,
            'client_ip': request.META['REMOTE_ADDR'],
            'session_id': session_id
            })

def payment_result(request, success):
    trans_id = request.GET['trans_id']
    session_id = request.GET['session_id']
    pay_type = request.GET['pay_type']
    error = request.GET.get('error' or None)

    if session_id and session_id != "":
        p = Payment.objects.get(session_id=session_id)
        p.trans_id = trans_id
        p.pay_type = pay_type
        p.error = error
        p.save()

    if success == True:
        msg = "Vaše platba byla úspěšně přijata."
    else:
        msg = "Vaše platba se nezdařila"

    return render_to_response('registration/payment_result.html',
                              {
            'pay_type': pay_type,
            'message': msg
            })

def make_sig(values):
    key1 = 'eac82603809d388f6a2b8b11471f1805'
    print "".join(values+(key1,))
    return hashlib.md5("".join(values+(key1,))).hexdigest()

def check_sig(sig, values):
    key2 = 'c2b52884c3816d209ea6c5e7cd917abb'
    if sig != hashlib.md5("".join(values+(key2,))).hexdigest():
        raise ValueError("Zamítnuto")

def payment_status(request):
    # Read notification parameters
    pos_id = request.POST['pos_id']
    session_id = request.POST['session_id']
    ts = request.POST['ts']
    sig = request.POST['sig']
    check_sig(sig, (pos_id, session_id, ts))
    # Determine the status of transaction based on the notification
    c = httplib.HTTPSConnection("www.payu.cz")
    timestamp = str(int(time.time()))
    c.request("POST", "/paygw/UTF/Payment/get/txt/",
              urllib.urlencode({
                'pos_id': pos_id,
                'session_id': session_id,
                'ts': timestamp,
                'sig': make_sig((pos_id, session_id, timestamp))
                }),
              {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"})
    raw_response = c.getresponse().read()
    r = {}
    for i in [i.split(':',1) for i in raw_response.split('\n') if i != '']:
        r[i[0]] = i[1].strip()
    check_sig(r['trans_sig'], (r['trans_pos_id'], r['trans_session_id'], r['trans_order_id'],
                               r['trans_status'], r['trans_amount'], r['trans_desc'],
                               r['trans_ts']))
    # Update the corresponding payment
    try:
        p = Payment.objects.get(trans_id=r['trans_id'])
    except Exception, e:
        # This is an unkown transaction
        pass # TODO: Log it
    else:
        p.status = r['trans_status']
        if r['trans_recv'] != '':
            p.realized = r['trans_recv']
        p.save()
    # Return positive error code as per PayU protocol
    return http.HttpResponse("OK")

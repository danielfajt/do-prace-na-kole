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
import time, random, httplib, urllib, hashlib, datetime
# Django imports
from django.shortcuts import render_to_response, redirect
import django.contrib.auth
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMessage
from django.template import RequestContext
from django.db.models import Sum, Count
# Registration imports
import registration.signals, registration.backends
# Model imports
from django.contrib.auth.models import User
from models import UserProfile, Voucher, Trip, Answer, Question, Team, Payment, Subsidiary, Company
from forms import RegistrationFormDPNK, RegisterTeamForm, RegisterSubsidiaryForm, RegisterCompanyForm, RegisterTeamForm, ProfileUpdateForm, InviteForm, TeamAdminForm, TeamUserAdminForm, PaymentTypeForm
from django.conf import settings
from  django.http import HttpResponse
# Local imports
import util
from dpnk.email import approval_request_mail, register_mail, team_membership_approval_mail, team_membership_denial_mail, team_created_mail, invitation_mail

#decorator
def must_be_coordinator(fn):
    @login_required
    def wrapper(*args, **kwargs):
        request = args[0]
        team = request.user.userprofile.team
        if team.coordinator != request.user.userprofile:
            return HttpResponse(u'Nejste koordinátorem týmu "' + team.name + u'", nemáte tedy oprávnění editovat jeho údaje. Koordinátorem vašeho týmu je "' + unicode(team.coordinator) + u'", vy jste: "' + unicode(request.user.userprofile) + u'"', status=401)
        else:
            return fn(*args, **kwargs)
    return wrapper

#decorator
def must_be_approved_for_team(fn):
    @login_required
    def wrapper(*args, **kwargs):
        request = args[0]
        userprofile = request.user.userprofile
        if userprofile.approved_for_team == 'approved' or userprofile.team.coordinator == userprofile:
            return fn(*args, **kwargs)
        else:
            return HttpResponse(u'Vaše členství v týmu "' + userprofile.team.name + u'" nebylo odsouhlaseno. O ověření členství můžete požádat v <a href="/registrace/profil">profilu</a>.', status=401)
    return wrapper

def redirect(url):
    return HttpResponse("redirect:"+url)

def register(request, backend='registration.backends.simple.SimpleBackend',
             success_url=None, form_class=None,
             disallowed_url='registration_disallowed',
             template_name='registration/registration_form.html',
             extra_context=None,
             token=None,
             initial_email=None):

    backend = registration.backends.get_backend(backend)
    form_class = RegistrationFormDPNK

    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)

        form_company = RegisterCompanyForm(request.POST, prefix = "company")
        form_subsidiary = RegisterSubsidiaryForm(request.POST, prefix = "subsidiary")
        form_team = RegisterTeamForm(request.POST, prefix = "team")
        company_selected = request.POST['company_selected'] == "True"
        subsidiary_selected = request.POST['subsidiary_selected'] == "True"
        team_selected = request.POST['team_selected'] == "True"
        company_valid = True
        subsidiary_valid = True
        team_valid = True

        if company_selected:
            form_company = RegisterCompanyForm(prefix = "company")
            form.fields['company'].required = True
        else:
            company_valid = form_company.is_valid()
            form.fields['company'].required = False

        if subsidiary_selected:
            form_subsidiary = RegisterSubsidiaryForm(prefix = "subsidiary")
            form.fields['subsidiary'].required = True
        else:
            subsidiary_valid = form_subsidiary.is_valid()
            form.fields['subsidiary'].required = False

        if team_selected:
            form_team = RegisterTeamForm(prefix = "team")
            form.fields['team'].required = True
        else:
            team_valid = form_team.is_valid()
            form.fields['team'].required = False

        form_valid = form.is_valid()

        if form_valid and company_valid and subsidiary_valid and team_valid:
            company = None
            subsidiary = None
            team = None

            if not company_selected:
                company = form_company.save()
            else:
                company = Company.objects.get(id=form.data['company'])

            if not subsidiary_selected:
                subsidiary = form_subsidiary.save(commit=False)
                subsidiary.company = company
                form_subsidiary.save()
            else:
                subsidiary = Subsidiary.objects.get(id=form.data['subsidiary'])

            if not team_selected:
                team = form_team.save(commit=False)
                team.subsidiary = subsidiary
                form_team.save()

            new_user = backend.register(request, **form.cleaned_data)
            auth_user = django.contrib.auth.authenticate(
                username=request.POST['username'],
                password=request.POST['password1'])
            django.contrib.auth.login(request, auth_user)

            if new_user.userprofile.team.invitation_token == token or not team_selected:
                userprofile = new_user.userprofile
                userprofile.approved_for_team = 'approved'
                userprofile.save()

            if not team_selected:
                team.coordinator = new_user.userprofile
                team.save()
                success_url = "/registrace/pozvanky"
                team_created_mail(new_user)
            else:
                register_mail(new_user)

            if new_user.userprofile.approved_for_team != 'approved':
                approval_request_mail(new_user)

            return redirect(success_url)
    else:
        initial_company = None
        initial_subsidiary = None
        initial_team = None

        if token != None:
            team = Team.objects.get(nvitation_token=token)
            initial_company = team.subsidiary.company
            initial_subsidiary = team.subsidiary
            initial_team = team

        form = form_class(request, initial={'company': initial_company, 'subsidiary': initial_subsidiary, 'team': initial_team, 'email': initial_email})
        form_company = RegisterCompanyForm(prefix = "company")
        form_subsidiary = RegisterSubsidiaryForm(prefix = "subsidiary")
        form_team = RegisterTeamForm(prefix = "team")

        company_selected = True
        subsidiary_selected = True
        team_selected = True

    return render_to_response(template_name,
                              {'form': form,
                               'form_subsidiary': form_subsidiary,
                               'form_company': form_company,
                               'form_team': form_team,
                               'company_selected': company_selected,
                               'subsidiary_selected': subsidiary_selected,
                               'team_selected': team_selected,
                               }, context_instance=RequestContext(request))



def create_profile(user, request, **kwargs):
    from dpnk.models import UserProfile
    if request.POST['team_selected'] == "True":
        team = Team.objects.get(id=request.POST['team'])
    else:
        team = Team.objects.get(name=request.POST['team-name'])

    UserProfile(user = user,
                team = team,
                firstname = request.POST['firstname'],
                surname = request.POST['surname'],
                telephone = request.POST['telephone'],
                distance = request.POST['distance']
                ).save()
registration.signals.user_registered.connect(create_profile)

@login_required
def payment_type(request):
    # if request.user.userprofile.team.subsidiary.city.admission_fee == 0:
    #     return redirect('/registrace/profil')
    template_name='registration/payment_type.html'
    form_class = PaymentTypeForm

    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            if form.cleaned_data['payment_type'] == 'pay':
                return redirect('/registrace/platba')
            elif form.cleaned_data['payment_type'] == 'company':
                Payment(user=request.user.userprofile, amount=0, pay_type='fc', status=5).save()
            elif form.cleaned_data['payment_type'] == 'member':
                Payment(user=request.user.userprofile, amount=0, pay_type='am', status=5).save()

            return redirect('/registrace/profil')
    else:
        form = form_class()

    return render_to_response(template_name,
                              {'form': form
                               }, context_instance=RequestContext(request))

@login_required
def payment(request):
    if request.user.userprofile.team.subsidiary.city.admission_fee == 0:
        pass #return redirect('/registrace/profil')
    uid = request.user.id
    order_id = '%s-1' % uid
    session_id = "%sJ%d " % (order_id, int(time.time()))
    # Save new payment record
    p = Payment(session_id=session_id,
                user=UserProfile.objects.get(user=request.user),
                order_id = order_id,
                amount = request.user.userprofile.team.subsidiary.city.admission_fee,
                description = "Ucastnicky poplatek Do prace na kole")
    p.save()
    # Render form
    profile = UserProfile.objects.get(user=request.user)
    return render_to_response('registration/payment.html',
                              {
            'firstname': profile.firstname, # firstname
            'surname': profile.surname, # surname
            'email': profile.email, # email
            'amount': p.amount,
            'amount_hal': p.amount * 100, # v halerich
            'description' : p.description,
            'order_id' : p.order_id,
            'client_ip': request.META['REMOTE_ADDR'],
            'session_id': session_id
             }, context_instance=RequestContext(request))

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
        msg = "Vaše platba se nezdařila. Po přihlášení do svého profilu můžete zadat novou platbu."

    try:
        city = UserProfile.objects.get(user=request.user).team.city
    except TypeError, e:
        # Looks like sometimes we loose the session before user comes
        # back from PayU
        city = None

    return render_to_response('registration/payment_result.html',
                              {
            'pay_type': pay_type,
            'message': msg,
            'city': city
            }, context_instance=RequestContext(request))

def make_sig(values):
    key1 = 'eac82603809d388f6a2b8b11471f1805'
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
    p = Payment.objects.get(session_id=r['trans_session_id'])
    p.status = r['trans_status']
    if r['trans_recv'] != '':
        p.realized = r['trans_recv']
    p.save()

    if p.status == 99 or p.status == '99':
        if len(Voucher.objects.filter(user = p.user)) == 0:
            # Assign voucher to user
            v = random.choice(Voucher.objects.filter(user__isnull=True))
            v.user = p.user
            v.save()
            # Send user email confirmation and a voucher
            email = EmailMessage(subject=u"Platba Do práce na kole a slevový kupon",
                                 body=u"""Obdrželi jsme Vaši platbu startovného pro soutěž Do práce na kole.

Zaplacením startovného získáváte poukaz na designové triko kampaně Do
práce na kole 2012 (včetně poštovného a balného). Objednávku můžete
uskutečnit na adrese:

http://www.coromoro.com/designova_trika/detail/139-do-prace-na-kole-2012

Váš slevový kód pro nákup trička v obchodě Čoromoro je %s.

K jeho zadání budete vyzváni poté, co si vyberete velikost a přejdete
na svůj nákupní košík.

S pozdravem
Auto*Mat
""" % v.code,
                             from_email = u'Do práce na kole <kontakt@dopracenakole.net>',
                             to = [p.user.email()])
            email.send(fail_silently=True)

    # Return positive error code as per PayU protocol
    return http.HttpResponse("OK")

def login(request):
    return render_to_response('registration/payment_result.html',
                              {
            'pay_type': pay_type,
            'message': msg
            }, context_instance=RequestContext(request))

@login_required
def profile(request):

    days = util.days()
    weekdays = ['Po', 'Út', 'St', 'Čt', 'Pá']
    today = datetime.date.today()
    #today = datetime.date(year=2012, month=5, day=4)
    profile = request.user.get_profile()

    if request.method == 'POST':
        raise http.Http404 # No POST, competition already terminated
        if 'day' in request.POST:
            try:
                trip = Trip.objects.get(user = request.user.get_profile(),
                                        date = days[int(request.POST['day'])-1])
            except Trip.DoesNotExist:
                trip = Trip()
                trip.date = days[int(request.POST['day'])-1]
                trip.user = request.user.get_profile()
            trip.trip_to = request.POST.get('trip_to', False)
            trip.trip_from = request.POST.get('trip_from', False)
            trip.save()
        # Pre-calculate total number of trips into userprofile to save load
        trip_counts = Trip.objects.filter(user=profile).values('user').annotate(Sum('trip_to'), Sum('trip_from'))
        try:
            profile.trips = trip_counts[0]['trip_to__sum'] + trip_counts[0]['trip_from__sum']
        except IndexError:
            profile.trips = 0
        profile.save()
    try:
        voucher_code = Voucher.objects.filter(user=profile)[0].code
    except IndexError, e:
        voucher_code = ''

    # Render profile
    payment_status = profile.payment_status()
    team_members = UserProfile.objects.filter(team=profile.team, active=True)

    trips = {}
    for t in Trip.objects.filter(user=profile):
        trips[t.date] = (t.trip_to, t.trip_from)
    calendar = []

    counter = 0
    for i, d in enumerate(days):
        cd = {}
        cd['name'] = "%s %d.%d." % (weekdays[d.weekday()], d.day, d.month)
        cd['iso'] = str(d)
        cd['question_active'] = (d <= today)
        cd['trips_active'] = (d <= today) and (
            len(Answer.objects.filter(
                    question=Question.objects.get(date = d),
                    user=request.user.get_profile())) > 0)
        if d in trips:
            cd['default_trip_to'] = trips[d][0]
            cd['default_trip_from'] = trips[d][1]
            counter += int(trips[d][0]) + int(trips[d][1])
        else:
            cd['default_trip_to'] = False
            cd['default_trip_from'] = False
        cd['percentage'] = float(counter)/(2*(i+1))*100
        cd['percentage_str'] = "%.0f" % (cd['percentage'])
        cd['distance'] = counter * profile.distance
        calendar.append(cd)

    member_counts = []
    for member in team_members:
        member_counts.append({
                'name': str(member),
                'trips': member.trips,
                'percentage': float(member.trips)/(2*util.days_count())*100,
                'distance': member.trips * member.distance})
    if len(team_members):
        team_percentage = float(sum([m['trips'] for m in member_counts]))/(2*len(team_members)*util.days_count()) * 100
    else:
        team_percentage = 0
    team_distance = sum([m['distance'] for m in member_counts])

    #for user_position, u in enumerate(UserResults.objects.filter(city=profile.team.city)):
    #    if u.id == profile.id:
    #        break
    #user_position += 1

    #for team_position, t in enumerate(TeamResults.objects.filter(city=profile.team.city)):
    #    if t.id == profile.team.id:
    #        break
    #team_position += 1

    req_city = request.GET.get('mesto', None)
    if req_city and (req_city.lower() != profile.team.city.lower()):
        own_city = False
    else:
        own_city = True


    company_survey_answers = Answer.objects.filter(
        question_id=34, user__in = [m.id for m in team_members])
    if len(company_survey_answers):
        company_survey_by = company_survey_answers[0].user
        if company_survey_by == request.user.get_profile():
            company_survey_by = 'me'
    else:
        company_survey_by = None
    return render_to_response('registration/profile.html',
                              {
            'active': profile.active,
            'superuser': request.user.is_superuser,
            'user': request.user,
            'profile': profile,
            'team': profile.team,
            'payment_status': payment_status,
            'voucher': voucher_code,
            'team_members': ", ".join([str(p) for p in team_members]),
            'team_members_count': len(team_members),
            'calendar': calendar,
            'member_counts': member_counts,
            'team_percentage': team_percentage,
            'team_distance': team_distance,
            #'user_position': user_position,
            #'team_position': team_position,
            'req_city': req_city,
            'own_city': own_city,
            'company_survey_by': company_survey_by,
            'competition_state': settings.COMPETITION_STATE,
            'approved_for_team': request.user.userprofile.approved_for_team,
            }, context_instance=RequestContext(request))

def results(request, template):

    city = request.GET.get('mesto', None)

    #if city:
    #    user_by_percentage = UserResults.objects.filter(city=city)[:10]
    #    user_by_distance = UserResults.objects.filter(city=city).order_by('-distance')[:10]
    #    team_by_distance = TeamResults.objects.filter(city=city).order_by('-distance')[:20]
    #    team_by_percentage = TeamResults.objects.filter(city=city)
    #    user_count = UserResults.objects.filter(city=city).count()
    #    team_count = TeamResults.objects.filter(city=city).count()
    #else:
    #    user_by_percentage = UserResults.objects.all()[:10]
    #    user_by_distance = UserResults.objects.all().order_by('-distance')[:10]
    #    team_by_distance = TeamResults.objects.all().order_by('-distance')[:20]
    #    team_by_percentage = TeamResults.objects.all()
    #    user_count = UserProfile.objects.filter(active=True).count()
    #    team_count = Team.objects.all().count()

    return render_to_response(template,
                              {
            'user_by_percentage': user_by_percentage,
            'user_by_distance': user_by_distance,
            'team_by_percentage': team_by_percentage,
            'team_by_distance': team_by_distance,
            'city': city,
            'user_count': user_count,
            'team_count': team_count,
            }, context_instance=RequestContext(request))

@login_required
def update_profile(request,
            success_url = '/registrace/profil/'
                  ):
    create_team = False
    profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        form_team = RegisterTeamForm(request.POST, prefix = "team")
        create_team = 'id_team_selected' in request.POST
        team_valid = True

        if create_team:
            team_valid = form_team.is_valid()
            form.fields['team'].required = False
            form.Meta.exclude = ('team')
        else:
            form_team = RegisterTeamForm(prefix = "team")
            form.fields['team'].required = True
            form.Meta.exclude = ()

        form_valid = form.is_valid()

        if team_valid and form_valid:
            userprofile = form.save(commit=False)

            if create_team:
                team = form_team.save(commit=False)
                team.subsidiary = request.user.userprofile.team.subsidiary

                userprofile.team = team
                userprofile.coordinated_team = team
                userprofile.approved_for_team = 'approved'
                team.coordinator = userprofile

                form_team.save()

                userprofile.team = team
                success_url = "/registrace/pozvanky"
                request.session['success_url'] = '/registrace/profil'

                team_created_mail(userprofile.user)

            if request.user.userprofile.team != form.cleaned_data['team'] and not create_team:
                userprofile.approved_for_team = 'undecided'

            form.save()

            if userprofile.approved_for_team != 'approved':
                approval_request_mail(userprofile.user)

            return redirect(success_url)
    else:
        form = ProfileUpdateForm(instance=profile)
        form_team = RegisterTeamForm(prefix = "team")

    form.fields['team'].widget.underlying_form = form_team
    form.fields['team'].widget.create_team = create_team
    #if request.user.userprofile.team.coordinator == request.user.userprofile:
    #    del form.fields["team"]
    return render_to_response('registration/update_profile.html',
                              {'form': form
                               }, context_instance=RequestContext(request))

@login_required
@must_be_approved_for_team
def questionaire(request, template = 'registration/questionaire.html'):

    def get_questions(params):
        if not params.has_key('questionaire'):
            raise http.Http404
        questionaire = params['questionaire']
        if questionaire == 'player':
            if not params.has_key('day'):
                raise http.Http404
            try:
                iso_day = params['day']
                day = datetime.date(*[int(v) for v in iso_day.split('-')])
            except ValueError:
                raise http.Http404
            if day > datetime.date.today():
                raise http.Http404
            questions = [Question.objects.get(questionaire=questionaire, date=day)]
        elif questionaire == 'company':
            questions = Question.objects.filter(questionaire=questionaire).order_by('order')
        return (questionaire, questions)

    if request.method == 'POST':
        raise http.Http404 # No POST, competition already terminated
        questionaire, questions = get_questions(request.POST)
        choice_ids = [v for k, v in request.POST.items() if k.startswith('choice')]
        comment_ids = [int(k.split('-')[1]) for k, v in request.POST.items() if k.startswith('comment')]

        answers_dict = {}
        for question in questions:
            try:
                answer = Answer.objects.get(user = request.user.get_profile(),
                                            question = question)
                # Cleanup previous fillings
                answer.choices = []
            except Answer.DoesNotExist:
                answer = Answer()
                answer.user = request.user.get_profile()
                answer.question = question
            answer.save()
            answers_dict[question.id] = answer

        # Save choices
        for choice_id in choice_ids:
            choice = Choice.objects.get(id=choice_id)
            answer = answers_dict[choice.question.id]
            answer.choices.add(choice_id)
            answer.save()
        # Save comments
        for comment_id in comment_ids:
            answer = answers_dict[comment_id] # comment_id = question_id
            answer.comment = request.POST.get('comment-%d' % comment_id, '')
            answer.save()
        return http.HttpResponseRedirect('/registrace/profil/') # Redirect after POST
    else:
        questionaire, questions = get_questions(request.GET)
        for question in questions:
            try:
                question.choices = Choice.objects.filter(question=question)
            except Choice.DoesNotExist:
                question.choices = None
            try:
                answer = Answer.objects.get(
                    question=question,
                    user=request.user.get_profile())
                question.comment_prefill = answer.comment
                question.choices_prefill = [c.id for c in answer.choices.all()]
            except Answer.DoesNotExist:
                question.comment_prefill = ''
                question.choices_prefill = ''

        return render_to_response(template,
                                  {'user': request.user.get_profile(),
                                   'questions': questions,
                                   'questionaire': questionaire,
                                   'day': request.GET.get('day', '')
                                   }, context_instance=RequestContext(request))

@staff_member_required
def questions(request):
    questions = Question.objects.all().order_by('date')
    return render_to_response('admin/questions.html',
                              {'questions': questions
                               }, context_instance=RequestContext(request))

def _company_answers(uid):
    return Answer.objects.filter(user_id=uid,
                                 question__in=Question.objects.filter(questionaire='company'))

def _total_points(answers):
    total_points = 0
    for a in answers:
        for c in a.choices.all():
            # Points assigned based on choices
            if c.points:
                total_points += c.points
        # Additional points assigned manually
        total_points += a.points
    return total_points

@staff_member_required
def company_survey(request):
    companies = [(u.id, u.team.company, u.team.city, u.team.name, _total_points(_company_answers(u.id))) for u in
                 set([a.user for a in Answer.objects.filter(
                    question__in=Question.objects.filter(questionaire='company'))])]
    return render_to_response('admin/company_survey.html',
                              {'companies': sorted(companies, key = lambda c: c[4], reverse=True)
                               }, context_instance=RequestContext(request))

def company_survey_answers(request):
    answers = _company_answers(request.GET['uid'])
    team = UserProfile.objects.get(id=request.GET['uid']).team
    total_points = _total_points(answers)
    return render_to_response('admin/company_survey_answers.html',
                              {'answers': answers,
                               'team': team,
                               'total_points': total_points
                               }, context_instance=RequestContext(request))


@staff_member_required
def answers(request):
    question_id = request.GET['question']
    question = Question.objects.get(id=question_id)

    if request.method == 'POST':
        points = [(k.split('-')[1], v) for k, v in request.POST.items() if k.startswith('points-')]
        for p in points:
            answer = Answer.objects.get(id=p[0])
            answer.points = int(p[1])
            answer.save()

    answers = Answer.objects.filter(question_id=question_id)
    total_respondents = len(answers)
    count = {'Praha': {}, 'Brno': {}, 'Liberec': {}}
    count_all = {}
    respondents = {'Praha': 0, 'Brno': 0, 'Liberec': 0}
    choice_names = {}
    
    for a in answers:
        a.city = a.user.city()

    
    if question.type in ('choice', 'multiple-choice'):
        for a in answers:
            respondents[a.city] += 1
            for c in a.choices.all():
                try:
                    count[a.city][c.id] += 1;
                except KeyError:
                    count[a.city][c.id] = 1
                    choice_names[c.id] = c.text
                try:
                    count_all[c.id] += 1
                except KeyError:
                    count_all[c.id] = 1

    stat = {'Praha': [], 'Brno': [], 'Liberec': [], 'Celkem': []}
    for city, city_count in count.items():
        for k, v in city_count.items():
            stat[city].append((choice_names[k], v, float(v)/respondents[city]*100))
    for k, v in count_all.items():
        stat['Celkem'].append((choice_names[k], v, float(v)/total_respondents*100))

    def get_percentage(r):
        return r[2]
    for k in stat.keys():
        stat[k].sort(key=get_percentage, reverse=True)

    return render_to_response('admin/answers.html',
                              {'question': question,
                               'answers': sorted(answers, key=lambda a: a.city),
                               'stat': stat,
                               'total_respondents': total_respondents,
                               'choice_names': choice_names
                               }, context_instance=RequestContext(request))

def approve_for_team(userprofile, reason, approve=False, deny=False):
    if deny:
        if not reason:
            return 'no_message'
        userprofile.approved_for_team = 'denied'
        userprofile.save()
        team_membership_denial_mail(userprofile.user, reason)
        return 'denied'
    elif approve:
        userprofile.approved_for_team = 'approved'
        userprofile.save()
        user_approved = True
        team_membership_approval_mail(userprofile.user)
        return 'approved'

@login_required
def team_approval_request(request):
    approval_request_mail(request.user)
    return render_to_response('registration/request_team_approval.html',
                              context_instance=RequestContext(request))

@login_required
def invite(request, backend='registration.backends.simple.SimpleBackend',
             success_url=None, form_class=None,
             template_name='registration/invitation.html',
             extra_context=None):
    form_class = InviteForm

    if 'success_url' in request.session:
        success_url = request.session.get('success_url')

    if request.method == 'POST':
        form = form_class(data=request.POST)
        if form.is_valid():
            invitation_mail(request.user, [form.cleaned_data['email1'], form.cleaned_data['email2'], form.cleaned_data['email3'], form.cleaned_data['email4'] ])
            return redirect(success_url)
    else:
        form = form_class()
    return render_to_response(template_name,
                              {'form': form,
                              }, context_instance=RequestContext(request))

@must_be_coordinator
@login_required
def team_admin(request, backend='registration.backends.simple.SimpleBackend',
             success_url=None, form_class=None,
             template_name='registration/team_admin.html',
             extra_context=None):
    team = request.user.userprofile.team
    unapproved_users = []
    form_class = TeamAdminForm
    denial_message = 'unapproved'

    for userprofile in UserProfile.objects.filter(team = team, approved_for_team='undecided', active=True):
        denial_message = approve_for_team(userprofile, request.POST.get('reason-' + str(userprofile.id), ''), approve=request.POST.has_key('approve-' + str(userprofile.id)), deny=request.POST.has_key('deny-' + str(userprofile.id)))

    if request.method == 'POST' and denial_message == 'unapproved':
        form = form_class(data=request.POST, instance = team)
        if form.is_valid():
            form.save()
            return redirect(success_url)
    else:
        form = form_class(instance = team)

    for userprofile in UserProfile.objects.filter(team = team, active=True):
        unapproved_users.append({
            'name': (u'Jméno', unicode(userprofile)),
            'username': (u'Uživatel', userprofile.user),
            'state_name': (u'Stav', unicode(userprofile.get_approved_for_team_display())),
            'id': (None, userprofile.id),
            'state': (None, userprofile.approved_for_team),
            })

    team_members = UserProfile.objects.filter(team=team, active=True)

    return render_to_response(template_name,
                              {'form': form,
                               'unapproved_users': unapproved_users,
                                'team_members': ", ".join([str(p) for p in team_members]),
                                'denial_message': denial_message == 'no_message',
                                }, context_instance=RequestContext(request))

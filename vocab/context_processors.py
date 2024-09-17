from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from sieve.settings import ICE_CREAM_PRICE
from .models import History, Profile
from .services import user_services


def get_user_strike(request):
    today_date = timezone.now().date()
    yesterday_date = today_date - timedelta(days=1)
    strike = [0, 0]

    def strike_calculation():
        ok_dates = (History.objects.filter(ch_result=True, user=user)
                    .order_by('-ch_date')
                    .values_list('ch_date', flat=True)
                    .distinct()[:100])
        active = False
        cur_date = today_date
        if not ok_dates:
            return [0, 0]
        elif ok_dates[0] == today_date:
            active = True
        elif ok_dates[0] == yesterday_date:
            active = False
            cur_date = yesterday_date

        cnt = 0
        for day in ok_dates:
            if day == cur_date:
                cnt += 1
                cur_date -= timedelta(days=1)
            else:
                break
        return [cnt, active]

    if request.user.is_authenticated:
        user = request.user
        today_cons_days_varname = str(today_date) + '_cons_days'
        yesterday_cons_days_varname = str(today_date - timedelta(days=1)) + 'cons_days'

        if today_cons_days_varname in request.session:
            strike = request.session[today_cons_days_varname]
        else:   # о сегодняшнем strike нет данных в сессии
            if yesterday_cons_days_varname in request.session:
                ok_in_today = History.objects.filter(ch_result=True, user=user, ch_date=today_date).exists()
                if ok_in_today:
                    strike = [request.session[yesterday_cons_days_varname][0] + 1, True]
                    request.session[today_cons_days_varname] = strike
                else:
                    strike = [request.session[yesterday_cons_days_varname][0], False]
                    request.session[today_cons_days_varname] = strike
            else:
                strike = strike_calculation()
    return {'strike': strike}


def get_user_coins(request):
    coins, ice_cream = 0, 0
    if request.user.is_authenticated:
        user = request.user
        profile = Profile.objects.get(user=user)
        coins = profile.coins
        ice_cream = coins // ICE_CREAM_PRICE
        # ice_cream, coins = divmod(coins, 50)

    return {'coins': coins, 'ice_cream': ice_cream}


def add_is_editor_to_context(request):
    is_editor = False
    if request.user.is_authenticated:
        is_editor = request.user.groups.filter(name='Editors').exists()
    return {'is_editor': is_editor}


def get_user_treasure(request):
    treasure = 0
    if request.user.is_authenticated:
        user = request.user
        profile = Profile.objects.get(user=user)
        treasure = profile.treasure

    reward = None
    if treasure >= settings.TREASURE_THRESHOLD:
        reward_id = request.session.get('reward_id', 0)
        if reward_id:
            reward = user_services.get_reward_by_id(reward_id)
            a = 9
        else:
            reward = user_services.get_random_reward()
            request.session['reward_id'] = reward.id
            b = 12

    context = {
        'treasure': treasure,
        'reward': reward,
    }
    return context

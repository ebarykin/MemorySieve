import json
import random
import openpyxl
import pandas as pd
from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models.query import QuerySet
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpRequest
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from typing import Optional, Tuple
from sieve.settings import COINS_PER_LEARNED_WORD, COINS_PER_ANSWER
from .forms import LoginForm, OptedDictForm, ActiveDictForm, UsageForm, WordForm, UserRegistrationForm, UserEditForm, \
    ProfileEditForm, WordPictForm, AddDictionaryForm, HintTypeForm, WordImportForm
from .models import Profile, PersDict, PubDict, Word, History, UsageExample, WordPict, WordPronunciation, UniqueEngWord
from .services import user_services, word_services, stat_services, dict_services


@login_required
def all_dict(request):
    user_service = user_services.UserService(request.user)
    user_words = user_service.get_all_user_words()
    word_services.add_dict_name_to_words(user_words)
    context = {'user_words_with_dict_names': user_words}
    return render(request, 'vocab/all_dict.html', context)


def index(request):
    context = {'section': 'index'}
    return render(request, 'vocab/index.html', context)


def get_started(request):
    return render(request, 'vocab/get_started.html')


def about(request):
    return render(request, 'vocab/about.html')


@login_required
def engage_dictionaries(request):
    profile = Profile.objects.get(user=request.user)
    is_editor = request.user.groups.filter(name='Editors').exists()
    if is_editor:
        dictionaries = PubDict.objects.all().order_by('dict_name', '-published')
    else:
        dictionaries = PubDict.objects.filter(published=True).order_by('dict_name', '-published')

    user_opted_dicts = profile.public_dicts.all()
    user_opted_dicts_names = [item.dict_name for item in user_opted_dicts]

    form = OptedDictForm(opted_dicts=dictionaries, initial=user_opted_dicts_names)

    if request.method == 'POST':
        user_opted_dicts_names = request.POST.getlist('opted_dicts')
        profile.public_dicts.clear()
        for dict_name in user_opted_dicts_names:
            pub_dict = PubDict.objects.get(dict_name=dict_name)
            profile.public_dicts.add(pub_dict)
        profile.save()
        form = OptedDictForm(opted_dicts=dictionaries, initial=user_opted_dicts_names)

    context = {
        'dictionaries': dictionaries,
        'form': form,
    }
    return render(request, 'vocab/engage_dictionaries.html', context)


def training(request):
    user = request.user

    selected_dicts = request.session.get('active_dicts', [])
    user_service = user_services.UserService(user, selected_dicts)

    user_opted_dicts = user_service.get_user_opted_dicts()

    if request.method == 'POST':
        if 'user_translation' in request.POST:
            handle_user_translation(request, user_service)
        if 'active_dicts_update' in request.POST:
            active_dicts_form = ActiveDictForm(
                request.POST,
                active_dicts_=user_opted_dicts,
                initial=user_service.selected_dict_names
            )
            if active_dicts_form.is_valid():
                selected_dicts = active_dicts_form.cleaned_data['active_dicts_']

                user_service.update_selected_dict_names(selected_dicts)

                request.session['active_dicts'] = selected_dicts
                cache.delete(f'user_active_words_{user_service.user.id}')

    active_dicts_form = ActiveDictForm(active_dicts_=user_opted_dicts, initial=user_service.selected_dict_names)
    random_word, usage_examples = handle_get_random(user_service)
    if not random_word:
        messages.error(request,
                       'На сегодня у вас нет доступных слов для тренировки. Если вы хотите изучить новые слова - '
                       'добавьте интересующие вас словари!')
    context = {
        'random_word': random_word,
        'usage_examples': usage_examples,
        'active_dicts_form': active_dicts_form,
    }
    return render(request, 'vocab/training.html', context)


def handle_get_random(user_service) -> Tuple[Optional[Word], Optional[QuerySet]]:
    """Возвращает случайное слово и примеры его использования."""

    update_req = False if f'user_active_words_{user_service.user.id}' in cache else True
    if update_req:
        random_word = user_service.get_user_random_word()
    else:
        cache_key = f'user_active_words_{user_service.user.id}'
        words = cache.get(cache_key)
        random_word = user_services.take_random_word_from_list(user_service.user, words)

    usage_examples = None
    if random_word:
        hint_type = user_service.profile.hint_type
        random_word.hint = word_services.word_controller.get_hint(random_word.eng_word, hint_type)
        random_word.q_ok = word_services.get_q_ok(random_word, user_service.user)
        usage_examples = random_word.usage_examples.all()
        try:
            random_word.pict = WordPict.objects.filter(word=random_word).order_by('-id').first()
        except WordPict.DoesNotExist:
            random_word.pict = None
    return random_word, usage_examples


def handle_user_translation(request, user_service) -> None:
    """Обрабатывает ввод пользователя при переводе слова."""

    user_input: str = request.POST['user_translation']

    if user_input:
        eng_word: str = request.POST['eng_word']
        word_id = request.POST['word_id']
        word = get_object_or_404(Word, id=word_id)
        exist_entry = user_service.has_entry_today(word)
        if user_input.lower() == eng_word.lower() and not exist_entry:
            user_service.user_active_words_cache_update()
            user_service.log_user_entry(word, result=True)
            q_ok = request.POST["q_ok"]
            prize = 0
            if q_ok == '6':
                success_message = (
                    f'<img src="/static/img/coins.png" alt="Изображение"> Слово "{word}" выучено! '
                    f'За это начислено {COINS_PER_LEARNED_WORD} монет'
                )
                messages.success(request, success_message)
                prize = COINS_PER_LEARNED_WORD
            user_service.update_coins(prize + COINS_PER_ANSWER)

            user_service.update_treasure(1)  # Начисляем одну монету за правильный ввод слова

    return None


@login_required
def profile_dashboard(request, **kwargs):
    profile = get_object_or_404(Profile, user=request.user)
    try:
        statistics = stat_services.get_user_statistics(request.user)
        if not statistics:
            raise ValueError("Статистика не получена")
    except (ValueError, KeyError, TypeError) as e:
        statistics = {
            'words_stat': {},
            'pers_words_qty': 0,
            'pub_words_qty': 0,
            'total_words_qty': 0,
            'data_points': [],
            'words_learned': 0,
            'max_strike': 0,
            'active_days_count': 0,
            'calendar_img': '',
        }
        messages.error(request, f"Произошла ошибка: {e}")

    context = {
        'profile': profile,
        **statistics,
    }
    return render(request, 'vocab/profile_dashboard.html', context)


@login_required
def level_view(request, lvl):
    words_by_lvl = user_services.get_user_words_by_lvl(request.user, lvl)
    context = {
        'words_by_lvl': words_by_lvl,
        'lvl': lvl,
    }
    return render(request, 'vocab/level.html', context)


@login_required
def profile_settings(request, **kwargs):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        if 'hint_type' in request.POST:
            hint_type_form = HintTypeForm(request.POST, instance=profile)
            if hint_type_form.is_valid():
                profile.hint_type = hint_type_form.cleaned_data['hint_type']
                profile.save()
            else:
                messages.error(request, 'Форма недействительна, не сохраняем')

    initial_data = {'hint_type': profile.hint_type}
    hint_form = HintTypeForm(initial=initial_data)

    context = {
        'profile': profile,
        'hint_form': hint_form
    }
    return render(request, 'vocab/profile_settings.html', context)


@login_required()
def profile_edit(request, **kwargs):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        if 'remove_avatar_btn' in request.POST:
            profile.photo.delete()
            profile.photo = None
            profile.save()
            messages.success(request, 'Avatar removed successfully!')
            return redirect(reverse('profile_edit', args=[request.user]))  # Редирект с параметром

        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(instance=profile, data=request.POST, files=request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
        else:
            messages.error(request, 'Error updating your profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'vocab/profile_edit.html', context)


@login_required
def profile_delete(request, **kwargs):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # Генерация случайных чисел
    num1 = random.randint(1, 50)
    num2 = random.randint(1, 50)
    correct_answer = num1 + num2

    if request.method == 'POST' and request.POST.get('delete') == 'true':
        user.delete()
        logout(request)
        return redirect('index')

    context = {
        'profile': profile,
        'user': user,
        'num1': num1,
        'num2': num2,
        'expected_answer': correct_answer,
    }

    return render(request, 'vocab/profile_delete.html', context)


@login_required
def dictionary(request, dict_name):
    is_editor = request.user.groups.filter(name='Editors').exists()
    file_form = WordImportForm()
    word_form = WordForm(request.user)

    dict_ = dict_services.get_dict_instance(dict_name, request.user)
    dict_form = None if dict_name == 'personal' else AddDictionaryForm(instance=dict_)

    words = dict_.words.all()

    context = {
        'words': words,
        'dict_': dict_,
        'file_form': file_form,
        'word_form': word_form,
        'dict_form': dict_form,
        'dict_name': dict_name,
    }

    if request.method == 'POST' and (is_editor or dict_name == 'personal' or 'to_exel' in request.POST):
        return _handle_post_request(request, context)

    return render(request, 'vocab/dict.html', context)


def _handle_post_request(request, context):
    if 'dictionary_edit' in request.POST:
        return _handle_dictionary_edit(request, dict_=context['dict_'])
    elif 'word_add' in request.POST:
        return add_word_modal(request, dict_=context['dict_'])
    elif 'from_file' in request.POST:
        return _handle_from_file(request, context)
    elif 'to_exel' in request.POST:
        return _handle_to_excel(words=context['words'], dict_name=context['dict_name'])
    return render(request, 'vocab/dict.html', context)


def _handle_dictionary_edit(request, dict_):
    dict_form = AddDictionaryForm(request.POST, request.FILES, instance=dict_)
    if dict_form.is_valid():
        dict_form.save()
        return redirect('dictionary', dict_.slug)
    else:
        messages.error(request, "Ошибка при редактировании словаря.")
    return redirect('dictionary', dict_.slug)


def add_word_modal(request, dict_=None):
    if dict_ is None:
        dict_ = get_object_or_404(PersDict, user=request.user)
    if request.method == 'POST':
        word_form = WordForm(request.user, request.POST)
        usage_form = UsageForm(request.POST)
        if word_form.is_valid() and usage_form.is_valid():
            success, message = word_services.save_word_from_form(word_form.cleaned_data, usage_form.cleaned_data, dict_)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        else:
            messages.error(request, "Ошибка при заполнении формы.")

        return redirect('all_dict')


def _handle_from_file(request, context):
    form = WordImportForm(request.POST, request.FILES)
    if form.is_valid():
        file = request.FILES['file']
        replace_existing = form.cleaned_data['replace_existing']
        file_extension = file.name.split('.')[-1].lower()

        if file_extension == 'json':
            try:
                new_words = json.load(file)
            except json.JSONDecodeError:
                messages.error(request, 'Ошибка чтения файла: неверный формат JSON.')
                return render(request, 'vocab/dict.html', context)
            except Exception as e:
                messages.error(request, f'Ошибка при чтении файла: {e}')
                return render(request, 'vocab/dict.html', context)
        elif file_extension in ['xls', 'xlsx']:
            try:
                fixed_column_names = ['eng_word', 'rus_word', 'eng_sample', 'rus_sample']
                df = pd.read_excel(file, names=fixed_column_names)
                new_words = df.to_dict(orient='records')

            except Exception as e:
                messages.error(request, f'Ошибка при чтении файла: {e}')
                return render(request, 'vocab/dict.html', context)
        else:
            messages.error(request, 'Неверный формат файла. Пожалуйста, загрузите файл в формате JSON или XLS/XLSX.')
            return render(request, 'vocab/dict.html', context)

        dict_ = context['dict_']
        for word in new_words:
            eng_word = word.get('eng_word', '')
            existing_word = dict_.words.filter(eng_word=eng_word).first()
            if existing_word and not replace_existing:
                messages.error(request, f'В словаре {dict_.dict_name} уже есть слово {eng_word}.')
                continue
            word_obj = Word.objects.create(
                eng_word=word.get('eng_word', ''),
                rus_word=word.get('rus_word', ''),
            )
            UsageExample.objects.create(
                word=word_obj,
                eng_text=word.get('eng_sample', ''),
                rus_text=word.get('rus_sample', ''),
            )
            dict_.words.add(word_obj)
    return render(request, 'vocab/dict.html', context)


def _handle_to_excel(words, dict_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = dict_name
    headers = ['eng_word', 'rus_word', 'eng_sample', 'rus_sample']
    ws.append(headers)
    for word in words:
        usage_example = word.usage_examples.first()
        eng_text = usage_example.eng_text if usage_example else ''
        rus_text = usage_example.rus_text if usage_example else ''
        ws.append([word.eng_word,
                   word.rus_word,
                   eng_text,
                   rus_text]
                  )
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={dict_name}.xlsx'
    wb.save(response)
    return response


def add_dictionary(request):
    if request.method == 'POST':
        form = AddDictionaryForm(request.POST, request.FILES)
        if form.is_valid():
            dict_name = form.cleaned_data['dict_name']
            if PubDict.objects.filter(dict_name=dict_name).exists():
                messages.error(request, 'Словарь с таким именем уже существует.')
            else:
                new_dict = form.save(commit=False)
                new_dict.save()
                messages.success(request, f'Словарь {dict_name} успешно создан.')
                dict_slug = new_dict.slug
                return redirect('dictionary', dict_slug)
        else:
            messages.error(request, "Ошибка при заполнении формы.")
    else:
        form = AddDictionaryForm()

    context = {
        'form': form
    }
    return render(request, 'vocab/add_dictionary.html', context)


@login_required
def delete_dictionary(request: HttpRequest, dict_id: int) -> HttpResponse:
    """ Удаление словаря"""
    previous_url = request.META.get('HTTP_REFERER')
    dict_ = PubDict.objects.get(id=dict_id)
    is_editor = request.user.groups.filter(name='Editors').exists()
    if request.method == "POST" and is_editor:
        dict_.delete()
        messages.success(request, f'Словарь "{dict_.dict_name}" удален.')
        return redirect('engage_dictionaries')
    else:
        messages.error(request, 'К сожалению, у вас нет доступа для удаления словарей. '
                                'Пожалуйста, свяжитесь с администратором, если вам необходимы дополнительные права.')

    return redirect(previous_url)


def card(request: HttpRequest, dict_name: str, u_eng_word: str) -> HttpResponse:
    word = word_services.get_word_instance(dict_name, u_eng_word, user=request.user)
    word.pict = word_services.get_word_picture(word)
    word.oxf_url = word_services.URLService.get_oxf_url(u_eng_word)
    hist = History.objects.filter(word=word, user=request.user)

    context = {
        'word': word,
        "hist": hist,
        'dict_name': dict_name,
    }
    return render(request, 'vocab/card.html', context)


def edit_card(request: HttpRequest, dict_name: str, word_id: int) -> HttpResponse:
    word = get_object_or_404(Word, id=word_id)
    word.pict = word_services.get_word_picture(word)

    if request.method == 'POST':
        new_eng_word = request.POST.get('word-u_eng_word')  # Проверка есть ли измененное слово в этом же словаре

        duplicate_found, message = word_services.check_duplicate(dict_name, new_eng_word, word, user=request.user)
        if duplicate_found:
            messages.error(request, message)
            return HttpResponseRedirect(word.get_absolute_url())

        success, word_form, usage_form, word_pict_form = process_edit_forms(word, request)
        if success:
            messages.success(request, 'Все изменения успешно сохранены.')
            return HttpResponseRedirect(word.get_absolute_url())
        else:
            messages.error(
                request,
                f'Ошибка при сохранении. Форма была отправлена, но нам не удалось сохранить данные. '
                f'Проверьте правильность введённой информации и попробуйте ещё раз. '
                f'{word_form.errors}, {usage_form.errors}, {word_pict_form.errors}'
            )
            return HttpResponseRedirect(word.get_absolute_url())

    word_form, usage_form, word_pict_form = get_forms_for_editing(word, request.user)
    context = {
        'word': word,
        'word_form': word_form,
        'usage_form': usage_form,
        'word_pict_form': word_pict_form,
        'dict_name': dict_name
    }

    return render(request, 'vocab/edit_card_modal.html', context)


def get_forms_for_editing(word: Word, user: User, post_data=None, files=None) \
        -> Tuple[WordForm, BaseInlineFormSet, WordPictForm]:
    usage_form_set = inlineformset_factory(
        Word,
        UsageExample,
        form=UsageForm,
        fields=('eng_text', 'rus_text'),
        fk_name='word',
        extra=1,
    )
    word_form = WordForm(user, post_data, instance=word, prefix='word')
    usage_form = usage_form_set(post_data, instance=word, prefix='usage')
    word_pict_form = WordPictForm(post_data, files)
    return word_form, usage_form, word_pict_form


def process_edit_forms(word: Word, request: HttpRequest) -> Tuple[bool, WordForm, BaseInlineFormSet, WordPictForm]:
    word_form, usage_form, word_pict_form = get_forms_for_editing(word, request.user, request.POST, request.FILES)
    if word_form.is_valid() and usage_form.is_valid() and word_pict_form.is_valid():
        word_form.save()
        usage_form.save()

        picture = request.FILES.get('picture')
        if picture:
            word_pict = WordPict(word=word, picture=picture)
            word_pict.save()
        return True, word_form, usage_form, word_pict_form
    else:
        return False, word_form, usage_form, word_pict_form


async def get_oxf_data(request: HttpRequest, u_eng_word: str) -> JsonResponse:
    unique_word_instance = await sync_to_async(UniqueEngWord.objects.get)(u_eng_word=u_eng_word)
    # Получаем QuerySet
    us_pron_qs = await sync_to_async(WordPronunciation.objects.filter)(unique_word=unique_word_instance, accent='US')
    br_pron_qs = await sync_to_async(WordPronunciation.objects.filter)(unique_word=unique_word_instance, accent='UK')
    us_exists = await sync_to_async(us_pron_qs.exists)()
    br_exists = await sync_to_async(br_pron_qs.exists)()
    pronunciation_exists = us_exists and br_exists

    oxf_data = {}
    if pronunciation_exists:
        us_pronunciation = await sync_to_async(us_pron_qs.first)()
        br_pronunciation = await sync_to_async(br_pron_qs.first)()
        oxf_data['audio_url_us'] = us_pronunciation.audio_file.url
        oxf_data['audio_url_br'] = br_pronunciation.audio_file.url
        oxf_data['phons_us'] = br_pronunciation.transcription
        oxf_data['phons_br'] = br_pronunciation.transcription
    else:
        oxf_data = await sync_to_async(word_services.URLService().get_oxf_data)(u_eng_word)
        await word_services.URLService().save_oxf_data_to_db(unique_word_instance, oxf_data)

    result = {"oxf_data": oxf_data}
    return JsonResponse(result)


def delete_card(request, word_id):
    """ Удаление объекта карточки слова из раздела card"""
    if request.method == "POST":
        word = get_object_or_404(Word, id=word_id)
        word_services.delete_word(word)
        messages.success(request, f'Карточка {word.eng_word} удалена')
        return redirect('all_dict')
    return redirect('error404')


def error404(request):
    return render(request, 'vocab/error-404.html')


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user is not None:
                if user.is_active:
                    user_service = user_services.UserService(user)
                    reward_id = user_service.check_if_rewarded()
                    request.session['reward_id'] = reward_id
                    login(request, user)
                    return HttpResponse('Authenticated successfully')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
    return render(request, 'vocab/login.html', {'form': form})


def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            Profile.objects.create(user=new_user)
            new_user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, new_user)
            return render(request, 'vocab/register_done.html', {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()
    return render(request, 'vocab/register.html', {'user_form': user_form})


def register_done(request):
    return render(request, 'vocab/register_done.html', {'new_user': request.user})


def reward(request):
    user_service = user_services.UserService(request.user)
    user_service.reset_treasure()
    reward_id = request.session.get('reward_id')
    reward_instance = user_services.get_reward_by_id(reward_id)
    user_service.update_coins(reward_instance.earned_coins)

    request.session['reward_id'] = None
    previous_url = request.META.get('HTTP_REFERER')

    context = {
        "previous_url": previous_url,
        "reward": reward_instance,
    }
    return render(request, 'vocab/reward.html', context)

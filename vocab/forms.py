from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.forms import TextInput, ModelForm, EmailInput, Select
from .models import Profile, PubDict, Word, PersDict, UsageExample, WordPict, UniqueEngWord
from django import forms


class WordForm(ModelForm):

    u_eng_word = forms.CharField(
        label='English Word',
        required=True,
        validators=[
            RegexValidator(r'^[a-zA-Z\s\']+$', 'Only alphabetic characters, spaces, and apostrophes are allowed.')],
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': "form-control form-control-sm",
        })
    )

    class Meta:
        model = Word
        fields = ["rus_word", "synonym", "hint", "part_of_speech"]
        labels = {
            'rus_word': 'Перевод',
            'synonym': 'Синоним',
            'hint': 'Подсказка',
            'part_of_speech': 'Часть речи',
        }
        widgets = {
            'rus_word': forms.TextInput(attrs={
                'class': "form-control form-control-sm ",
            }),
            'synonym': forms.TextInput(attrs={
                'class': "form-control form-control-sm ",
            }),
            'hint': forms.TextInput(attrs={
                'class': "form-control form-control-sm ",
            }),
            'part_of_speech': forms.Select(attrs={
                'class': 'form-select-sm'
            })
        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(WordForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['u_eng_word'].initial = self.instance.u_eng_word.u_eng_word

    def save(self, commit=True):
        instance = super(WordForm, self).save(commit=False)
        instance.user = self.user  # Сохраняем текущего пользователя в модели
        word_is_new = instance.pk is None

        # Получаем или создаем объект UniqueEngWord на основе введенного текста
        u_eng_word_value = self.cleaned_data['u_eng_word']
        unique_eng_word, created = UniqueEngWord.objects.get_or_create(u_eng_word=u_eng_word_value)
        instance.u_eng_word = unique_eng_word

        instance.save()  # Сохраняем объект instance здесь
        # если слово новое - считаем, что его создал пользователь в свой персональный словарь
        # если это изменение существующего слова, то в PersDict останется запись автора слова
        if word_is_new:
            # Создаем или получаем объект PersDict для текущего пользователя
            pers_dict, created = PersDict.objects.get_or_create(user=self.user)
            # Добавляем созданное слово к words в PersDict
            pers_dict.words.add(instance)
        return instance

    #  Собственная проверка. Подумать что можно добавить при валидации формы
    def clean_eng_word(self):
        u_eng_word = self.cleaned_data['u_eng_word']
        if len(u_eng_word) < 2:
            raise forms.ValidationError('Длина слова должна быть не менее 3х символов')
        return u_eng_word


class AddDictionaryForm(ModelForm):
    class Meta:
        model = PubDict
        fields = ['dict_name', 'description', 'level', 'published', 'picture']
        widgets = {
            'dict_name': TextInput(attrs={
                'class': "form-control form-control fs-5 py-0 border-0 fw-bold mb-0",
                'placeholder': 'dict_name'
            }),
            'description': TextInput(attrs={
                'class': "form-control form-control fs-6 py-0 border-0 mb-0",
                'placeholder': 'description'
            }),
            'level': forms.Select(choices=PubDict.LVL),
            'published': forms.CheckboxInput(),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control-file'})

        }


class UsageForm(ModelForm):
    class Meta:
        model = UsageExample
        fields = ['eng_text', 'rus_text']
        widgets = {
            'eng_text': forms.Textarea(attrs={
                'class': 'form-control form-control sm',
                'style': 'height: 3em; overflow-wrap: break-word; '


            }),
            'rus_text': forms.Textarea(attrs={
                'class': 'form-control form-control sm',
                'style': 'height: 3em; overflow-wrap: break-word; '
            })
        }


class TrainingForm(forms.Form):
    check_word = forms.CharField(max_length=30)


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Password',
                               widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repeat password',
                                widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']

    def clean_email(self):
        data = self.cleaned_data['email']
        if User.objects.filter(email=data).exists():
            raise forms.ValidationError('Email already in use.')
        return data


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': "form-control",
                'placeholder': 'Имя'
            }),
            'last_name': forms.TextInput(attrs={
                'class': "form-control form-control-sm",
                'placeholder': 'Фамилия'
            }),
            'email': EmailInput(attrs={
                'class': "form-control form-control-sm",
                'placeholder': 'Ваш email'
            }),
            'username': forms.TextInput(attrs={
                'class': "form-control form-control-sm",
                'placeholder': 'Ваш username'
            })
        }

    def clean_email(self):
        data = self.cleaned_data['email']
        qs = User.objects.exclude(id=self.instance.id).filter(email=data)
        if qs.exists():
            raise forms.ValidationError('Email already in use.')
        return data


# class CustomClearableFileInput(forms.ClearableFileInput):
#     template_name = 'avatar_clearable_file_input.html'


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'photo', 'interests']
        widgets = {
            # 'photo': CustomClearableFileInput(attrs={'class': 'btn btn-primary-soft btn-sm mb-0'}),
            'photo': forms.FileInput(attrs={'class': 'form-control d-none', 'id': 'uploadfile-1'}),
            # 'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': "form-control form-control-sm",
            }),
            'interests': forms.Textarea(attrs={
                'class': "form-control form-control-sm",
                'placeholder': 'Ваши интересы',
                'rows': 3
            })
        }


class WordPictForm(forms.ModelForm):
    class Meta:
        model = WordPict
        fields = ['picture']
        widgets = {
            # 'picture': CustomClearableFileInput(attrs={'class': 'btn btn-primary-soft btn-sm mb-0'}),
            'picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class OptedDictForm(forms.Form):
    opted_dicts = forms.ChoiceField(label='Выберите словари')

    def __init__(self, *args, **kwargs):
        opted_dicts = kwargs.pop('opted_dicts', None)
        initial = kwargs.pop('initial', None)
        super().__init__(*args, **kwargs)

        if opted_dicts:
            dict_choices = [(dict_instance.dict_name, dict_instance.dict_name) for dict_instance in opted_dicts]
            self.fields['opted_dicts'].choices = dict_choices
            self.fields['opted_dicts'].initial = initial


class ActiveDictForm(forms.Form):
    active_dicts_ = forms.MultipleChoiceField(label='Словари', widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        active_dicts_ = kwargs.pop('active_dicts_', None)

        initial = kwargs.pop('initial', None)
        super().__init__(*args, **kwargs)

        if active_dicts_:
            dict_choices = [('personal', 'personal')] + [(dict_instance.dict_name, dict_instance.dict_name) for
                                                         dict_instance
                                                         in active_dicts_]

            self.fields['active_dicts_'].choices = dict_choices
        else:
            dict_choices = [('personal', 'personal')]
            self.fields['active_dicts_'].choices = dict_choices
        self.fields['active_dicts_'].initial = initial


class HintTypeForm(ModelForm):
    class Meta:
        model = Profile
        fields = ('hint_type',)
        widgets = {
            'hint_type': Select(attrs={'class': 'form-control'}),
        }


class WordImportForm(forms.Form):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'accept': '.json, .xls, .xlsx'}))
    replace_existing = forms.BooleanField(required=False)

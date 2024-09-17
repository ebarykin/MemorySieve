from django.contrib import admin
from .models import Word, PersDict, PubDict, History, WordPict, Profile, Reward


# class MyHistAdmin(admin.ModelAdmin):
#     list_display = ('user', 'word', 'ch_date', 'ch_result')
#     list_filter = ('user', 'word', 'ch_result')
#

# admin.site.register(MyHist, MyHistAdmin)

class HistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'word', 'ch_date', 'ch_result')
    list_filter = ('user', 'word', 'ch_result')


admin.site.register(History, HistoryAdmin)
admin.site.register(WordPict)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'photo']
    raw_id_fields = ['user']


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ('id', 'u_eng_word', 'eng_word', 'rus_word', 'part_of_speech', 'synonym', 'hint')


@admin.register(PersDict)
class PersDictAdmin(admin.ModelAdmin):
    list_display = ('user',)


@admin.register(PubDict)
class PubDictAdmin(admin.ModelAdmin):
    list_display = ['dict_name']


# @admin.register(WordPict)
# class WordPictAdmin(admin.ModelAdmin):
#     list_display = ['picture', 'description']
#
#
@admin.register(Reward)
class RewardImageAdmin(admin.ModelAdmin):
    list_display = ['img_path', 'earned_coins', 'message']

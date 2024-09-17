import matplotlib.pyplot as plt
import calplot
import pandas as pd
from io import BytesIO
import base64
from django.contrib.auth.models import User
from vocab.models import History
from django.db.models import Count
from datetime import datetime


class CalendarPlot:
    def __init__(self):
        self.year = int(datetime.now().year)
        self.figsize = (15, 8)
        self.dpi = 300
        self.cmap = 'YlGn'
        self.edgecolor = 'cornflowerblue'
        self.dropzero = True

    def create_plot(self, user: User) -> str:
        active_days = (History.objects
                       .filter(user=user)
                       .values('ch_date')
                       .annotate(record_count=Count('id'))
                       .order_by('ch_date')
                       )

        if not active_days.exists():  # Если данных нет создаем пустую серию данных с датами для текущего года
            date_range = pd.date_range(start=f'{self.year}-01-01', end=f'{self.year}-12-31', freq='D')
            series = pd.Series(0, index=date_range)
        else:
            series = queryset_to_series(active_days)

        plt.figure(figsize=self.figsize, dpi=self.dpi)
        calplot.yearplot(series,
                         cmap=self.cmap,
                         dayticks=True,
                         textformat='{:.0f}',
                         year=self.year,
                         edgecolor=self.edgecolor,
                         dropzero=self.dropzero)

        fig = plt.gcf()

        with BytesIO() as buf:
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return image_base64


def queryset_to_series(queryset, date_field='ch_date', count_field='record_count'):
    dates = [entry[date_field] for entry in queryset]
    dates = pd.to_datetime(dates)
    data = [entry[count_field] for entry in queryset]
    series = pd.Series(data, index=dates)
    return series

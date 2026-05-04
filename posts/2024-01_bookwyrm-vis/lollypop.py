import altair as alt
import pandas as pd

# Assuming books_df is your dataframe with columns: finish_date, pages
# Extract year from finish_date and aggregate data
books_df['year'] = pd.to_datetime(books_df['finish_date']).dt.year

# Aggregate by year
yearly_stats = books_df.groupby('year').agg(
    total_books=('year', 'size'),
    total_pages=('pages', 'sum')
).reset_index()

min_year = yearly_stats['year'].min().astype(int)
max_year = yearly_stats['year'].max().astype(int)

# Create the lollipop plot
# Points (dots) for the lollipops
points = alt.Chart(yearly_stats).mark_point(
    filled=True,
    color=col_bw_green
).encode(
    x=alt.X('year:Q'),
    y=alt.Y('total_books:Q'),
    size=alt.Size('total_pages:Q', 
                  title='Total Pages',
                  scale=alt.Scale(range=[100, 1000]),
                  legend=alt.Legend(symbolFillColor='steelblue')),
    tooltip=[
        alt.Tooltip('year:O', title='Year'),
        alt.Tooltip('total_books:Q', title='Books Read'),
        alt.Tooltip('total_pages:Q', title='Total Pages', format=',')
    ]
).interactive()

# Base chart for the stems (lines)
stems = alt.Chart(yearly_stats).mark_rule(
    size=2,
    color= col_bw_green
).encode(
    x=alt.X('year:Q', 
            title='Year', 
            axis=alt.Axis(
                labelAngle=0,
                tickCount=10,
                format='d',
                values=[years for years in range(min_year-1, max_year+1, 5)]
            ),
            scale=alt.Scale(zero=False)),
    y=alt.Y('total_books:Q', title='Total Books Read'),
    tooltip=[
        alt.Tooltip('year:O', title='Year'),
        alt.Tooltip('total_books:Q', title='Books Read'),
        alt.Tooltip('total_pages:Q', title='Total Pages', format=',')
    ]
)



# Combine both charts
chart = (points + stems).properties(
    width=600,
    height=400,
    title='Books Read Per Year'
).configure_axis(
    labelFontSize=12,
    titleFontSize=14
).configure_title(
    fontSize=16,
    anchor='start'
)

chart
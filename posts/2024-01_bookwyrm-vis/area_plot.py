import altair as alt
import pandas as pd

# Assuming books_df is your dataframe with columns: finish_date, author_text, gender
# Extract year from finish_date
books_metadata_df['year'] = pd.to_datetime(books_metadata_df['finish_date']).dt.year

# Count books by year and gender
gender_by_year = books_metadata_df.groupby(['year', 'gender']).size().reset_index(name='count')

# Calculate percentage for each gender within each year
gender_by_year['total_by_year'] = gender_by_year.groupby('year')['count'].transform('sum')
gender_by_year['percentage'] = (gender_by_year['count'] / gender_by_year['total_by_year']) * 100

# Create normalized stacked area chart
chart = alt.Chart(gender_by_year).mark_area(
    opacity=0.8,
    interpolate='monotone'
).encode(
    x=alt.X('year:Q', 
            title='Year',
            axis=alt.Axis(format='d', tickCount=10)),
    y=alt.Y('percentage:Q',
            title='Percentage of Authors (%)',
            stack='normalize',
            axis=alt.Axis(format='.0f')),
    color=alt.Color('gender:N',
                    title='Gender',
                    scale=alt.Scale(scheme='category10')),
    tooltip=[
        alt.Tooltip('year:Q', title='Year', format='d'),
        alt.Tooltip('gender:N', title='Gender'),
        alt.Tooltip('count:Q', title='Books Read'),
        alt.Tooltip('percentage:Q', title='Percentage', format='.1f')
    ]
).properties(
    width=700,
    height=400,
    title='Author Gender Distribution Over Time (Normalized)'
).interactive()

chart

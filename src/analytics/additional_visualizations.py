"""Generate additional analytical views of the validated prison statistics."""
from pathlib import Path
import json
import math
import matplotlib.pyplot as plt
import pandas as pd
from src.preprocessing.selection import load_descriptive_view



def add_additional_views(root, records):
    root = Path(root)
    tables = root / 'results/tables/descriptive'
    output = root / 'results/plots'
    audit = root / 'results/tables/visualization'
    audit.mkdir(parents=True, exist_ok=True)
    latest = pd.read_csv(tables / 'latest_state_snapshot.csv')
    balanced = pd.read_csv(tables / 'year_summary_balanced.csv')
    statuses = pd.read_csv(tables / 'demographic_status_year.csv')
    year = int(latest.year.max())
    def finish(name, kind, data, inference, reason, source):
        plt.tight_layout()
        plt.savefig(output / (name+'.png'), dpi=300, bbox_inches='tight')
        plt.close()
        data.to_csv(audit / (name+'.csv'), index=False)
        records.append(dict(file=name+'.png',kind=kind,source=source,
                            plot_data='results/tables/visualization/'+name+'.csv',
                            suitability=reason,inference=inference))
    # Keep rankings within a single year rather than adding repeated annual stocks.
    fig, axes = plt.subplots(1,2,figsize=(14,6))
    for ax, field, title in zip(axes,['convicts','under_trial'],['Convicts','Undertrials']):
        d=latest.nlargest(10,field).sort_values(field)
        ax.barh(d.state,d[field]);ax.set_title(title);ax.set_xlabel('Reported inmates (count)')
    fig.suptitle(f'Largest convicted and undertrial populations, {year}')
    finish('11_status_state_rankings','Paired bars',latest[['state','year','convicts','under_trial']],
           f"Largest convict population: {latest.loc[latest.convicts.idxmax(),'state']}; largest undertrial population: {latest.loc[latest.under_trial.idxmax(),'state']}.",
           'Separate status rankings reveal differences hidden by total population.','latest_state_snapshot.csv')
    # Gender and caste panels share a status-specific denominator.
    caste=statuses[(statuses.source=='Caste.csv') & (statuses.year==year) & statuses.legal_status.isin(['convicts','under_trial'])]
    gender=[]
    for status in ['convicts','under_trial']:
        for sex in ['male','female']:
            gender.append(dict(legal_status=status,category=sex,prisoners=int(latest[sex+'_'+status].sum())))
    gender=pd.DataFrame(gender)
    fig,axes=plt.subplots(2,2,figsize=(12,11))
    for j,status in enumerate(['convicts','under_trial']):
        for i,data in enumerate([gender,caste]):
            d=data[data.legal_status==status]
            axes[i,j].pie(d.prisoners,autopct='%1.1f%%',labels=d.category)
            axes[i,j].set_title(('Gender' if i==0 else 'Caste')+' — '+status)
    fig.suptitle(f'Status-specific composition, {year}; eligible source coverage')
    combined=pd.concat([gender.assign(dimension='gender'),caste.assign(dimension='caste')],ignore_index=True)
    finish('12_status_demographics','Composition panels',combined,
           f"Female shares are {100*gender[(gender.legal_status=='convicts') & (gender.category=='female')].prisoners.sum()/gender[gender.legal_status=='convicts'].prisoners.sum():.2f}% among convicts and {100*gender[(gender.legal_status=='under_trial') & (gender.category=='female')].prisoners.sum()/gender[gender.legal_status=='under_trial'].prisoners.sum():.2f}% among undertrials. Caste and gender are overlapping margins.",
           'Compare observed compositions within convicted and undertrial populations.','latest_state_snapshot.csv; demographic_status_year.csv')
    death=load_descriptive_view(root,'Death_sentence.csv')
    fields=['no_capital_punishment','no_life_imprisonment']
    current=death[death.year==year]
    fig,axes=plt.subplots(1,2,figsize=(14,6))
    for ax,field in zip(axes,fields):
        d=current.nlargest(10,field).sort_values(field);ax.barh(d.state,d[field]);ax.set_xlabel('Reported indicator count');ax.set_title(field)
    fig.suptitle(f'Death-sentence source indicators by jurisdiction, {year}')
    finish('14_sentence_indicator_rankings','Indicator rank panels',current[['state','year']+fields],
           'These source field names are retained literally; no_life_imprisonment is not assumed to describe every life-sentenced inmate.',
           'Compare source-specific indicators without confusing them with the entire sentenced population.','Death_sentence.csv, eligible cleaned view')
    complete=death.groupby('state').year.nunique();fixed=death[death.state.isin(complete[complete==13].index)]
    annual=fixed.groupby('year')[fields].sum().reset_index()
    fig,axes=plt.subplots(2,1,figsize=(10,8),sharex=True)
    for ax,field in zip(axes,fields):ax.bar(annual.year,annual[field]);ax.set_ylabel('Indicator count');ax.set_title(field)
    axes[-1].set_xlabel('Year');fig.suptitle(f'Death-sentence indicators: fixed {fixed.state.nunique()}-jurisdiction coverage')
    finish('15_sentence_indicator_trends','Annual indicator panels',annual,
           f'Trends use the same {fixed.state.nunique()} jurisdictions in all thirteen years; the two indicators are not added together.',
           'Prevent geographic coverage changes from masquerading as indicator changes.','Death_sentence.csv, eligible cleaned view')
    fig,axes=plt.subplots(1,2,figsize=(14,7))
    pieces=[]
    for ax,source,status in zip(axes,['Religion.csv','Education.csv'],['under_trial','convicts']):
        d=statuses[(statuses.source==source)&(statuses.year==year)&(statuses.legal_status==status)].sort_values('prisoners')
        ax.barh(d.category,d.share_within_status*100);ax.set_xlabel('Share within covered legal-status population (%)');ax.set_title(source+' — '+status)
        pieces.append(d)
    finish('16_religion_education','Demographic share bars',pd.concat(pieces),
           'Religion uses the explicitly repaired religion column; these two panels describe different legal-status populations.',
           'Labeled bars make small categories easier to compare than crowded pie slices.','demographic_status_year.csv')
    crime=load_descriptive_view(root,'IPC_crime_inmates_convicted.csv')
    measures=[c for c in crime if c.startswith(('Male ','Female '))]
    crime=crime.assign(reported_count=crime[measures].sum(axis=1))
    current=crime[crime.year==year]
    totals=current.groupby('CRIME HEAD').reported_count.sum().sort_values()
    plt.figure(figsize=(11,9));plt.barh(totals.index,totals.values);plt.xlabel('Reported convicted IPC counts');plt.title(f'Convicted IPC composition, {year}; {current.state.nunique()} jurisdictions')
    finish('17_ipc_composition','Crime composition bars',totals.rename('reported_count').reset_index(),
           f"Murder represents {100*totals['MURDER']/totals.sum():.2f}% of this source's reported convicted IPC counts, not all prisoners or resident crime incidence.",
           'Compare all 21 heads without an unreadable 21-slice pie.','IPC_crime_inmates_convicted.csv, eligible cleaned view')
    complete=crime.groupby('state').year.nunique();fixed=crime[crime.state.isin(complete[complete==13].index)]
    groups={
      'women_related':['CRUELTY BY HUSBAND OR RELATIVE OF HUSBAND','EVE-TEASING','MOLESTATION','DOWRY DEATHS','RAPE'],
      'property':['BURGLARY','DACOITY','PREP. AND ASSEMBLY FOR DACOITY','ROBBERY','THEFTS'],
      'fraud':['CHEATING','COUNTER FEITING','CRIMINAL BREACH OF TRUST'],
      'other_selected':['ARSON','ATTEMPT TO COMMIT MURDER','C.H. NOT AMOUNTING TO MURDER','KIDNAPPING AND ABDUCTION','OTHER IPC CRIMES','RIOTS'],
      'murder':['MURDER']}
    for index,(name,heads) in enumerate(groups.items(),18):
        rows=math.ceil(len(heads)/2);fig,axes=plt.subplots(rows,2,figsize=(14,3.5*rows),squeeze=False)
        trend=fixed[fixed['CRIME HEAD'].isin(heads)].groupby(['year','CRIME HEAD']).reported_count.sum().reset_index()
        for ax,head in zip(axes.flat,heads):
            d=trend[trend['CRIME HEAD']==head];ax.plot(d.year,d.reported_count,marker='o');ax.set_title(head,fontsize=10);ax.set_xlabel('Year');ax.set_ylabel('Reported inmate count')
        for ax in list(axes.flat)[len(heads):]:ax.set_visible(False)
        fig.suptitle(f'Convicted IPC head trends: fixed {fixed.state.nunique()} jurisdictions')
        finish(f'{index:02d}_crime_trends_{name}','Crime trend facets',trend,
               f"For {heads[0]}, reported counts change from {int(trend[(trend.year==trend.year.min()) & (trend['CRIME HEAD']==heads[0])].reported_count.sum()):,} to {int(trend[(trend.year==trend.year.max()) & (trend['CRIME HEAD']==heads[0])].reported_count.sum()):,} over 2001–2013 on {fixed.state.nunique()} fixed jurisdictions. These are convicted-inmate counts, not crime incidence.",
               'Separate axes retain interpretable scales for different source crime heads.','IPC_crime_inmates_convicted.csv, eligible fixed-coverage view')
        rows=math.ceil(len(heads)/2);fig,axes=plt.subplots(rows,2,figsize=(14,3.5*rows),squeeze=False)
        ranking=current[current['CRIME HEAD'].isin(heads)][['state','year','CRIME HEAD','reported_count']]
        for ax,head in zip(axes.flat,heads):
            d=ranking[ranking['CRIME HEAD']==head].nlargest(10,'reported_count').sort_values('reported_count')
            ax.barh(d.state,d.reported_count);ax.set_title(head,fontsize=10);ax.set_xlabel('Reported convicted inmate count')
        for ax in list(axes.flat)[len(heads):]:ax.set_visible(False)
        fig.suptitle(f'Convicted IPC head rankings, {year}; top ten per head')
        finish(f'{index+5:02d}_crime_rankings_{name}','Crime ranking facets',ranking,
               f"For {heads[0]}, {ranking[ranking['CRIME HEAD']==heads[0]].nlargest(1,'reported_count').state.iloc[0]} has the largest reported count ({int(ranking[ranking['CRIME HEAD']==heads[0]].reported_count.max()):,}) in {year}. This is not a per-resident crime rate.",
               'Compare jurisdictions within each crime head without pooling repeated annual inmate stocks.','IPC_crime_inmates_convicted.csv, eligible latest-year view')
    return records

"""Generate reproducible descriptive plots without running mining algorithms."""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def run_visualization(root):
    root = Path(root)
    tables = root / "results/tables/descriptive"
    output = root / "results/plots"
    output.mkdir(exist_ok=True, parents=True)
    sns.set_theme(style="whitegrid")
    latest = pd.read_csv(tables / "latest_state_snapshot.csv")
    panel = pd.read_csv(tables / "state_year_totals.csv")
    profiles = pd.read_csv(root / "data/processed/transformed/profile_features.csv")
    year = pd.read_csv(tables / "year_summary_balanced.csv")
    demo = pd.read_csv(tables / "demographic_year.csv")
    records = []
    def save(name, kind, source, reason, inference):
        plt.tight_layout()
        plt.savefig(output / (name + ".png"), dpi=300, bbox_inches="tight")
        plt.close()
        records.append(dict(file=name+".png", kind=kind, source=source, suitability=reason, inference=inference))
    plt.figure(figsize=(10,6))
    top = latest.nlargest(10,"total_prisoners").sort_values("total_prisoners")
    plt.barh(top.state,top.total_prisoners);plt.xlabel("Reported prisoners (count)");plt.title("Largest reported prison populations, 2013")
    save("01_bar","Bar","latest_state_snapshot.csv","Compare jurisdiction counts.",f"Uttar Pradesh reports {int(top.total_prisoners.max()):,} prisoners, the largest count.")
    plt.figure(figsize=(7,7))
    status = demo[(demo.year==2013)&(demo.dimension=="legal_status")]
    wedges, *_ = plt.pie(status.prisoners,autopct=lambda pct: f"{pct:.1f}%" if pct >= 2 else "");plt.legend(wedges, [f"{name}: {100*count/status.prisoners.sum():.2f}%" for name,count in zip(status.category,status.prisoners)], loc="lower center", bbox_to_anchor=(.5,-.15));plt.title("Reported legal-status composition, 2013 (35 jurisdictions)")
    save("02_pie","Pie","demographic_year.csv","Mutually exclusive statuses form one population.","Undertrials account for 67.60% of the 411,992 reported prisoners.")
    plt.figure(figsize=(8,5));plt.hist(profiles.occupancy_ratio*100,bins=20,edgecolor="white");plt.xlabel("Occupancy (% of capacity)");plt.ylabel("State-year profiles (count)");plt.title("Occupancy distribution, 437 selected profiles")
    save("03_histogram","Histogram","profile_features.csv","Show the numeric occupancy distribution.",f"The median occupancy is {profiles.occupancy_ratio.median()*100:.2f}%; the maximum is {profiles.occupancy_ratio.max()*100:.0f}%.")
    plt.figure(figsize=(10,5));sns.boxplot(data=panel,x="year",y="occupancy_ratio");plt.xlabel("Year");plt.ylabel("Occupancy ratio (1 = full capacity)");plt.title("Jurisdiction occupancy distributions by year; available coverage")
    save("04_box","Box plot","state_year_totals.csv","Compare medians, dispersion and extreme observations.","Coverage changes from 34 to 35 jurisdictions after 2008; outliers are retained.")
    plt.figure(figsize=(8,5));plt.plot(year.year,year.prisoners,marker="o",label="Prisoners");plt.plot(year.year,year.capacity,marker="s",label="Capacity");plt.legend();plt.xlabel("Year");plt.ylabel("Reported count / capacity places");plt.title("Population and capacity: fixed 34-jurisdiction panel")
    save("05_line","Line","year_summary_balanced.csv","Display temporal changes with fixed geographic coverage.","Prisoner counts grew 31.33%, compared with 51.41% capacity growth over 2001–2013.")
    plt.figure(figsize=(8,5));plt.scatter(profiles.illiterate_share*100,profiles.occupancy_ratio*100,alpha=.5);plt.xlabel("Illiterate share (% of prisoners)");plt.ylabel("Occupancy (% of capacity)");plt.title("Aggregate profile association: 437 state-years")
    save("06_scatter","Scatter","profile_features.csv","Inspect paired numerical values without causal claims.","Pooled Pearson correlation is 0.35432; repeated state-years are not independent people.")
    plt.figure(figsize=(8,6));sns.heatmap(profiles.drop(columns=["profile_id","state","year"]).corr(),annot=True,fmt=".2f",vmin=-1,vmax=1,cmap="vlag");plt.title("Pearson correlations of five profile features")
    save("07_heatmap","Heatmap","profile_features.csv","Compare all feature-pair associations on one consistent cohort.","The largest absolute off-diagonal Pearson correlation is 0.35432, between illiterate share and occupancy.")
    plt.figure(figsize=(8,5));plt.stackplot(year.year,year.convicts,year.undertrials,year.detenues,year.others,labels=["Convicts","Undertrials","Detenues","Others"]);plt.legend(loc="upper left");plt.xlabel("Year");plt.ylabel("Reported prisoners (count)");plt.title("Legal-status counts: fixed 34-jurisdiction panel")
    save("08_area","Stacked area","year_summary_balanced.csv","Show disjoint category contributions through time.","Undertrials remain the largest category throughout the fixed-panel series.")
    plt.figure(figsize=(9,7));d=latest.nlargest(15,"occupancy_ratio").sort_values("occupancy_ratio");plt.plot(d.occupancy_ratio*100,d.state,"o");plt.axvline(100,color="red",linestyle="--");plt.xlabel("Occupancy (% of capacity)");plt.title("Highest occupancy jurisdictions, 2013")
    save("09_dot","Dot plot","latest_state_snapshot.csv","Precisely compare a manageable number of numeric values.","Chhattisgarh has the highest reported occupancy at 260.96%; Delhi follows at 216.83%.")
    values=sorted(int(round(v*100)) for v in latest.occupancy_ratio)
    stems={}
    for value in values:stems.setdefault(value//10,[]).append(value%10)
    text="Stem | Leaves\n"+"\n".join(f"{stem:>4} | "+" ".join(map(str,leaves)) for stem,leaves in stems.items())
    fig,ax=plt.subplots(figsize=(8,9));ax.axis("off");ax.text(.05,.95,text,va="top",family="monospace",fontsize=11);ax.set_title("2013 occupancy stem-and-leaf display\nKey: 11 | 8 = 118% (rounded to nearest percentage point)")
    save("10_stem_leaf","Stem-and-leaf","latest_state_snapshot.csv","Retain individual rounded values for 35 jurisdictions.","The display includes recorded zero occupancy and a rounded maximum of 261%; rounding is for this display only.")
    from src.analytics.additional_visualizations import add_additional_views
    records = add_additional_views(root, records)
    (output / "plot_catalog.json").write_text(json.dumps(records,indent=2)+"\n")
    return records

if __name__ == "__main__":
    run_visualization(Path(__file__).resolve().parents[2])

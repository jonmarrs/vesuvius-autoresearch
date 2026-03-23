import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_results():
    if not os.path.exists('results.tsv'):
        print("No results.tsv found.")
        return

    # Read the TSV
    try:
        df = pd.read_csv('results.tsv', sep='\t')
        if df.empty:
            print("results.tsv is empty.")
            return
        if 'timestamp' not in df.columns:
            print(f"results.tsv missing 'timestamp' column. Columns found: {df.columns}")
            return
    except Exception as e:
        print(f"Failed to read/parse results.tsv: {e}")
        return
    
    # Convert timestamp to datetime for better plotting
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except Exception as e:
        print(f"Failed to convert timestamps: {e}")
        return
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Create the plot
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot val_bpb (primary metric - lower is better)
    color = 'tab:blue'
    ax1.set_xlabel('Time')
    ax1.set_ylabel('val_bpb (lower is better)', color=color)
    ax1.plot(df['timestamp'], df['val_bpb'], marker='o', color=color, linewidth=2, label='val_bpb')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_yscale('log') # Log scale since bpb can vary widely

    # Create a second y-axis for throughput
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Throughput (Mvps)', color=color)
    ax2.plot(df['timestamp'], df['throughput_Mvps'], marker='x', color=color, linestyle='--', alpha=0.6, label='Throughput')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Vesuvius Autoresearch: Autonomous Research Progress')
    fig.tight_layout()
    
    # Annotate significant points (e.g., model scale jumps)
    for i, row in df.iterrows():
        if i == 0 or row['num_params_M'] != df.iloc[i-1]['num_params_M']:
            ax1.annotate(f"{row['num_params_M']}M params", 
                         (row['timestamp'], row['val_bpb']),
                         textcoords="offset points", 
                         xytext=(0,10), 
                         ha='center',
                         fontsize=8,
                         bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.3))

    plt.savefig('progress.png')
    print("Updated progress.png")

if __name__ == "__main__":
    plot_results()

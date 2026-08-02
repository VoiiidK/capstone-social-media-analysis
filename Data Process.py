import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from scipy import stats
import calendar
import warnings
import os
import glob
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Chinese character
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

class Analyzer:
    def __init__(self, output_folder='./analysis_results'):
        self.weibo_data_all = {}
        self.x_data_all = {}
        self.combined_data = None
        self.results = {}
        self.weibo_files_info = []
        self.x_files_info = []
        self.output_folder = output_folder
        
        # Output folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
    
    def extract_account_name(self, filename):
        """Extract account name from filename"""
        basename = os.path.basename(filename)
        name_without_ext = os.path.splitext(basename)[0]
        
        if '_' in name_without_ext:
            return name_without_ext.split('_', 1)[1]
        else:
            return name_without_ext
    
    def _safe_read_csv(self, file_path, platform, encoding='utf-8'):
        """Only read first two columns"""
        try:
            # Try to read only first two columns
            return pd.read_csv(file_path, encoding=encoding, usecols=[0, 1])
        except Exception as e:
            print(f"First read failed: {e}, trying alternative method...")
            try:
                # Try different encoding, read only first two columns
                return pd.read_csv(file_path, encoding='latin-1', usecols=[0, 1])
            except Exception as e2:
                print(f"Specified column read failed: {e2}, trying to read all columns then keep first two...")
                try:
                    # Read all columns first, then keep first two
                    df = pd.read_csv(file_path, encoding=encoding)
                    if len(df.columns) >= 2:
                        df = df.iloc[:, :2]  # Keep only first two columns
                        # Rename columns
                        if platform == 'weibo':
                            df.columns = ['publish_time', 'content'] if len(df.columns) == 2 else ['publish_time', 'content', 'temp']
                        else:
                            df.columns = ['created_at', 'content'] if len(df.columns) == 2 else ['created_at', 'content', 'temp']
                        # Remove temporary column
                        if len(df.columns) > 2:
                            df = df.iloc[:, :2]
                        return df
                    else:
                        print(f"File has less than 2 columns: {len(df.columns)} columns")
                        return pd.DataFrame()
                except Exception as e3:
                    print(f"All read methods failed: {e3}")
                    return pd.DataFrame()
    
    def load_weibo_folder(self, folder_path):
        weibo_files = glob.glob(os.path.join(folder_path, "*.csv"))
        print(f"Found {len(weibo_files)} Weibo data files")
        
        all_dfs = []
        files_info = []
        
        for file_path in weibo_files:
            try:
                account_name = self.extract_account_name(file_path)
                print(f"Loading Weibo account: {account_name}")
                df = self._safe_read_csv(file_path, 'weibo')
                
                if df is None or df.empty:
                    print(f"File is empty or read failed")
                    continue
                
                # Check column names and rename
                if len(df.columns) >= 2:
                    df.columns = ['content', 'publish_time'][:len(df.columns)]
                
                df['publish_time'] = df['publish_time'].astype(str)
                valid_dates = df['publish_time'].str.contains(r'\d{4}-\d{2}-\d{2}', na=False)
                df = df[valid_dates]
                    
                if len(df) > 0:
                    df['publish_time'] = pd.to_datetime(df['publish_time'])
                    df['platform'] = 'Weibo'
                    df['account_name'] = account_name
                    df['account_id'] = os.path.basename(file_path).split('_')[0]
                    df['brand'] = account_name  # Add brand column for frequency analysis
                        
                    all_dfs.append(df)
                    self.weibo_data_all[account_name] = df
                        
                    # Save file
                    files_info.append({
                        'file_name': os.path.basename(file_path),
                        'brand': account_name,
                        'records': len(df),
                        'time_range': (df['publish_time'].min(), df['publish_time'].max())
                    })
                        
                    print(f"{len(df)} records loaded")
                else:
                    print(f"No valid date data, skipping")
                
            except Exception as e:
                print(f"Loading failed {file_path}: {e}")
        
        self.weibo_files_info = files_info
        
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        else:
            return None
    
    def load_x_folder(self, folder_path):
        x_files = glob.glob(os.path.join(folder_path, "*.csv"))
        print(f"Found {len(x_files)} X data files")
        
        all_dfs = []
        files_info = []
        
        for file_path in x_files:
            try:
                account_name = self.extract_account_name(file_path)
                print(f"Loading X account: {account_name}")
                
                df = self._safe_read_csv(file_path, 'x')
                
                if df is None or df.empty:
                    print(f"File is empty or read failed")
                    continue
                
                df = df.dropna(subset=['created_at'])
                df['created_at'] = pd.to_datetime(df['created_at'])
                df['platform'] = 'X'
                df['account_name'] = account_name
                df['account_id'] = os.path.basename(file_path).split('_')[0] if '_' in os.path.basename(file_path) else 'unknown'
                df['brand'] = account_name  # Add brand column for frequency analysis
                    
                # Rename columns
                column_mapping = {
                    'created_at': 'publish_time', 
                    'likes': 'like_num', 
                    'retweets': 'forward_num', 
                    'replies': 'comment_num'
                }
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                    
                all_dfs.append(df)
                self.x_data_all[account_name] = df
                    
                # Save
                files_info.append({
                    'file_name': os.path.basename(file_path),
                    'brand': account_name,
                    'records': len(df),
                    'time_range': (df['publish_time'].min(), df['publish_time'].max())
                })
                    
                print(f"{len(df)} records loaded")
                
            except Exception as e:
                print(f"Loading failed {file_path}: {e}")
        
        self.x_files_info = files_info
        
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        else:
            return None
    
    def combine_all_data(self, weibo_folder, x_folder):
        weibo_combined = self.load_weibo_folder(weibo_folder)
        x_combined = self.load_x_folder(x_folder)
        
        if weibo_combined is not None and x_combined is not None:
            self.combined_data = pd.concat([weibo_combined, x_combined], ignore_index=True)
            
            # Extract time features
            self.combined_data['hour'] = self.combined_data['publish_time'].dt.hour
            self.combined_data['day_of_week'] = self.combined_data['publish_time'].dt.dayofweek
            self.combined_data['day_name'] = self.combined_data['publish_time'].dt.day_name()
            self.combined_data['month'] = self.combined_data['publish_time'].dt.month
            self.combined_data['date'] = self.combined_data['publish_time'].dt.date
            
            print(f"\nData combination completed")
            print(f"Total records: {len(self.combined_data)}")
            print(f"Weibo accounts: {len(self.weibo_data_all)}")
            print(f"X accounts: {len(self.x_data_all)}")
            
            weibo_accounts = list(self.weibo_data_all.keys())
            x_accounts = list(self.x_data_all.keys())
            print(f"Weibo accounts: {weibo_accounts}")
            print(f"X accounts: {x_accounts}")
            
            return self.combined_data
        else:
            print("Data loading failed")
            return None
    
    def analyze_account_level_patterns(self):
        """Analyze time patterns for each account"""
        if self.combined_data is None:
            print("Load data first")
            return None
        
        account_results = {}
        
        for (platform, account_name), group_data in self.combined_data.groupby(['platform', 'account_name']):
            print(f"Analyzing {platform} - {account_name}")
            
            # Basic statistics
            total_posts = len(group_data)
            date_range = group_data['publish_time'].max() - group_data['publish_time'].min()
            avg_daily_posts = total_posts / max(1, date_range.days)
            
            # Daily patterns
            daily_pattern = group_data['day_of_week'].value_counts().sort_index()
            peak_day = daily_pattern.idxmax() if len(daily_pattern) > 0 else -1
            peak_day_count = daily_pattern.max() if len(daily_pattern) > 0 else 0
            
            # Hourly patterns (only for Weibo)
            if platform == 'Weibo':
                hourly_pattern = group_data['hour'].value_counts().sort_index()
                peak_hour = hourly_pattern.idxmax() if len(hourly_pattern) > 0 else -1
                peak_hour_count = hourly_pattern.max() if len(hourly_pattern) > 0 else 0
                hourly_distribution = hourly_pattern.to_dict()
            else:
                peak_hour = -1
                peak_hour_count = 0
                hourly_distribution = {}
            
            account_results[(platform, account_name)] = {
                'total_posts': total_posts,
                'date_range_days': date_range.days,
                'avg_daily_posts': avg_daily_posts,
                'peak_hour': peak_hour,
                'peak_hour_count': peak_hour_count,
                'peak_day': peak_day,
                'peak_day_name': calendar.day_name[peak_day] if peak_day != -1 else 'No data',
                'peak_day_count': peak_day_count,
                'hourly_distribution': hourly_distribution,
                'daily_distribution': daily_pattern.to_dict()
            }
        
        self.results['account_level'] = account_results
        return account_results
    
    def calculate_frequency_metrics(self, platform_key):
        if platform_key == 'weibo':
            data = self.combined_data[self.combined_data['platform'] == 'Weibo']
        else:
            data = self.combined_data[self.combined_data['platform'] == 'X']
            
        if data is None or len(data) == 0:
            return None

        time_col = 'publish_time'
        start_date = data[time_col].min().normalize()
        end_date = data[time_col].max().normalize()
        full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        daily_posts = data.groupby(data[time_col].dt.date).size()
        daily_posts = daily_posts.reindex(full_date_range.date, fill_value=0)
        
        brands_daily = {}
        brands_stats = {}
        
        for brand in data['brand'].unique():
            brand_data = data[data['brand'] == brand]
            brand_daily = brand_data.groupby(brand_data[time_col].dt.date).size()
            brand_daily = brand_daily.reindex(full_date_range.date, fill_value=0)
            brands_daily[brand] = brand_daily
            
            # Detailed statistics
            brand_daily_values = brand_daily.values
            brands_stats[brand] = {
                'total_posts': brand_daily.sum(),
                'mean_daily': brand_daily.mean(),
                'median_daily': np.median(brand_daily_values),
                'std_daily': brand_daily.std(),
                'max_daily': brand_daily.max(),
                'min_daily': brand_daily.min(),
                'active_days': (brand_daily > 0).sum(),
                'active_rate': (brand_daily > 0).sum() / len(brand_daily) * 100
            }
        
        # Basic statistics
        total_days = len(full_date_range)
        total_posts = len(data)
        posts_per_day = total_posts / total_days if total_days > 0 else 0
        
        # Moving average
        daily_series = pd.Series(daily_posts.values, index=full_date_range)
        moving_avg_7d = daily_series.rolling(window=7, min_periods=1).mean()
        moving_avg_30d = daily_series.rolling(window=30, min_periods=1).mean()
        
        metrics = {
            'platform': platform_key,
            'total_posts': total_posts,
            'total_days': total_days,
            'posts_per_day': posts_per_day,
            'max_posts_per_day': daily_posts.max(),
            'min_posts_per_day': daily_posts.min(),
            'median_posts_per_day': np.median(daily_posts.values),
            'std_posts_per_day': daily_posts.std(),
            'daily_posts': daily_posts,
            'brands_daily': brands_daily,
            'brands_stats': brands_stats,
            'moving_avg_7d': moving_avg_7d,
            'moving_avg_30d': moving_avg_30d,
            'date_range': (start_date, end_date),
            'brands': list(data['brand'].unique()),
            'brands_count': len(data['brand'].unique()),
            'full_date_range': full_date_range
        }
        
        return metrics
    
    def analyze_frequency_patterns(self):
        print("\nStarting frequency pattern analysis")
        
        platforms_data = [
            ('weibo', 'Weibo'),
            ('x', 'X Platform')
        ]
        
        frequency_results = {}
        
        for platform_key, platform_name in platforms_data:
            metrics = self.calculate_frequency_metrics(platform_key)
            if metrics:
                frequency_results[platform_key] = metrics
                self._print_frequency_metrics_summary(metrics, platform_name)
        
        self.results['frequency'] = frequency_results
        return frequency_results
    
    def _print_frequency_metrics_summary(self, metrics, platform_name):
        print(f"\n{platform_name} Posting Frequency Analysis Results")
        print(f"Total posts: {metrics['total_posts']}")
        print(f"Analysis days: {metrics['total_days']}")
        print(f"Brand count: {metrics['brands_count']}")
        print(f"Average daily posts: {metrics['posts_per_day']:.2f}")
        print(f"Max daily posts: {metrics['max_posts_per_day']}")
        print(f"Min daily posts: {metrics['min_posts_per_day']}")
        print(f"Median daily posts: {metrics['median_posts_per_day']}")
        print(f"Standard deviation: {metrics['std_posts_per_day']:.2f}")
        print(f"Time range: {metrics['date_range'][0].strftime('%Y-%m-%d')} to {metrics['date_range'][1].strftime('%Y-%m-%d')}")
        print(f"Brand list: {', '.join(metrics['brands'])}")
    
    # Visualization Methods
    
    def visualize_total_posts_comparison(self):
        """Chart 1: Total posts comparison by account"""
        if 'account_level' not in self.results:
            print("Run account level analysis first")
            return
        
        account_results = self.results['account_level']
        
        accounts = []
        platforms = []
        total_posts = []
        
        for (platform, account_name), stats in account_results.items():
            accounts.append(account_name)
            platforms.append(platform)
            total_posts.append(stats['total_posts'])
        
        plt.figure(figsize=(10, 6))
        colors = ['#FF6B6B' if p == 'Weibo' else '#4ECDC4' for p in platforms]
        bars = plt.barh(accounts, total_posts, color=colors, alpha=0.7)
        
        plt.xlabel('Total Posts', fontsize=12)
        plt.title('Total Posts Comparison by Account', fontsize=14, fontweight='bold')
        
        # Add values on bars
        for bar, count in zip(bars, total_posts):
            plt.text(bar.get_width() + max(total_posts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{count}', va='center', fontsize=10, fontweight='bold')
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#FF6B6B', label='Weibo Accounts'),
            Patch(facecolor='#4ECDC4', label='X Platform Accounts')
        ]
        plt.legend(handles=legend_elements, loc='lower right')
        
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/1_Total_Posts_Comparison.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Chart generated: 1_Total_Posts_Comparison.png")
    
    def visualize_daily_posts_comparison(self):
        """Chart 2: Average daily posts comparison by account"""
        if 'account_level' not in self.results:
            return
        
        account_results = self.results['account_level']
        
        accounts = []
        platforms = []
        avg_daily = []
        
        for (platform, account_name), stats in account_results.items():
            accounts.append(account_name)
            platforms.append(platform)
            avg_daily.append(stats['avg_daily_posts'])
        
        plt.figure(figsize=(10, 6))
        colors = ['#FF6B6B' if p == 'Weibo' else '#4ECDC4' for p in platforms]
        bars = plt.barh(accounts, avg_daily, color=colors, alpha=0.7)
        
        plt.xlabel('Average Daily Posts', fontsize=12)
        plt.title('Average Daily Posts Comparison by Account', fontsize=14, fontweight='bold')
        
        for bar, count in zip(bars, avg_daily):
            plt.text(bar.get_width() + max(avg_daily)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{count:.2f}', va='center', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/2_Average_Daily_Posts_Comparison.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Chart generated: 2_Average_Daily_Posts_Comparison.png")
    
    def visualize_peak_hour_distribution(self):
        """Chart 3: Weibo accounts peak hour distribution"""
        if 'account_level' not in self.results:
            return
        
        account_results = self.results['account_level']
        
        # Only Weibo accounts' peak hours
        weibo_hours = []
        weibo_accounts = []
        
        for (platform, account_name), stats in account_results.items():
            if platform == 'Weibo' and stats['peak_hour'] != -1:
                weibo_hours.append(stats['peak_hour'])
                weibo_accounts.append(account_name)
        
        if weibo_hours:
            plt.figure(figsize=(10, 6))
            plt.hist(weibo_hours, bins=24, alpha=0.7, color='#FF6B6B', edgecolor='black', range=(0, 24))
            plt.xlabel('Peak Hour', fontsize=12)
            plt.ylabel('Number of Weibo Accounts', fontsize=12)
            plt.title('Weibo Accounts Peak Hour Distribution', fontsize=14, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.xticks(range(0, 24, 2))
            
            plt.tight_layout()
            plt.savefig(f'{self.output_folder}/3_Weibo_Peak_Hour_Distribution.png', dpi=300, bbox_inches='tight')
            plt.show()
            
            print("Chart generated: 3_Weibo_Peak_Hour_Distribution.png")
        else:
            print("No Weibo account data available for peak hour analysis")
    
    def visualize_platform_distribution(self):
        """Chart 4: Platform distribution pie chart"""
        if 'account_level' not in self.results:
            return
        
        account_results = self.results['account_level']
        
        platforms = [platform for (platform, _) in account_results.keys()]
        platform_counts = pd.Series(platforms).value_counts()
        
        plt.figure(figsize=(8, 6))
        plt.pie(platform_counts.values, labels=platform_counts.index, 
                autopct='%1.1f%%', colors=['#FF6B6B', '#4ECDC4'], 
                startangle=90, textprops={'fontsize': 12})
        plt.title('Account Platform Distribution', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/4_Platform_Distribution.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Chart generated: 4_Platform_Distribution.png")
    
    def visualize_weibo_hourly_patterns(self):
        """Chart 5: Weibo accounts hourly posting pattern heatmap"""
        if self.combined_data is None:
            return
        
        # Only analyze Weibo data
        weibo_data = self.combined_data[self.combined_data['platform'] == 'Weibo']
        if weibo_data.empty:
            print("No Weibo data available for hourly pattern analysis")
            return
        
        hourly_pivot = weibo_data.pivot_table(
            index='account_name',
            columns='hour',
            values='publish_time',
            aggfunc='count',
            fill_value=0
        )
        
        plt.figure(figsize=(12, 8))
        sns.heatmap(hourly_pivot, annot=True, fmt='d', cmap='Reds', 
                   cbar_kws={'label': 'Post Count'}, linewidths=0.5)
        plt.title('Weibo Accounts Hourly Posting Pattern Heatmap', fontsize=14, fontweight='bold')
        plt.xlabel('Hour', fontsize=12)
        plt.ylabel('Weibo Account', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/5_Weibo_Hourly_Posting_Heatmap.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Chart generated: 5_Weibo_Hourly_Posting_Heatmap.png")
    
    def visualize_daily_patterns_comparison(self):
        """Chart 6: Daily posting patterns comparison by platform"""
        if self.combined_data is None:
            return
        
        daily_pivot = self.combined_data.pivot_table(
            index='platform',
            columns='day_of_week',
            values='publish_time',
            aggfunc='count',
            fill_value=0
        )
        
        # Rename days of week
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_pivot.columns = day_names
        
        plt.figure(figsize=(10, 6))
        daily_pivot.T.plot(kind='bar', figsize=(12, 6), color=['#FF6B6B', '#4ECDC4'])
        plt.title('Daily Posting Patterns Comparison by Platform', fontsize=14, fontweight='bold')
        plt.xlabel('Day of Week', fontsize=12)
        plt.ylabel('Post Count', fontsize=12)
        plt.legend(title='Platform')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/6_Platform_Daily_Patterns_Comparison.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Chart generated: 6_Platform_Daily_Patterns_Comparison.png")
    
    def visualize_account_daily_patterns(self):
        """Chart 7: Daily posting patterns heatmap by account"""
        if self.combined_data is None:
            return
        
        daily_pivot = self.combined_data.pivot_table(
            index=['platform', 'account_name'],
            columns='day_of_week',
            values='publish_time',
            aggfunc='count',
            fill_value=0
        )
        
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_pivot.columns = day_names
        
        plt.figure(figsize=(14, 10))
        sns.heatmap(daily_pivot, annot=True, fmt='d', cmap='YlOrBr', 
                   cbar_kws={'label': 'Post Count'}, linewidths=0.5)
        plt.title('Daily Posting Patterns Heatmap by Account', fontsize=14, fontweight='bold')
        plt.xlabel('Day of Week', fontsize=12)
        plt.ylabel('Platform - Account', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/7_Account_Daily_Patterns_Heatmap.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Chart generated: 7_Account_Daily_Patterns_Heatmap.png")
    
    def visualize_frequency_timeseries(self):
        """Chart 8: Brand posting time series"""
        if 'frequency' not in self.results:
            return
        
        for platform_key, metrics in self.results['frequency'].items():
            platform_name = 'Weibo' if platform_key == 'weibo' else 'X Platform'
            
            plt.figure(figsize=(15, 8))
            colors = plt.cm.Set3(np.linspace(0, 1, len(metrics['brands'])))
            
            for i, (brand, daily_posts) in enumerate(metrics['brands_daily'].items()):
                dates = pd.date_range(start=metrics['date_range'][0], 
                                    end=metrics['date_range'][1], freq='D')
                plt.plot(dates, daily_posts.values, 
                        label=f'{brand}', 
                        color=colors[i],
                        alpha=0.7, linewidth=2)
            
            plt.title(f'{platform_name} Daily Post Count by Brand', fontsize=16, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Post Count')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True, alpha=0.3)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f'{self.output_folder}/8_{platform_name}_Brand_Posting_Timeseries.png', dpi=300, bbox_inches='tight')
            plt.show()
            print(f"Chart generated: 8_{platform_name}_Brand_Posting_Timeseries.png")
    
    def visualize_platform_comparison(self):
        """Chart 9: Platform overall comparison"""
        if 'frequency' not in self.results:
            return
        
        plt.figure(figsize=(15, 8))
        for platform_key, metrics in self.results['frequency'].items():
            platform_name = 'Weibo' if platform_key == 'weibo' else 'X Platform'
            dates = pd.date_range(start=metrics['date_range'][0], 
                                end=metrics['date_range'][1], freq='D')
            plt.plot(dates, metrics['daily_posts'].values, 
                    label=f'{platform_name} (Avg: {metrics["posts_per_day"]:.2f}/day)', 
                    linewidth=2)
        
        plt.title('Platform Overall Posting Trend', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Total Post Count')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/9_Platform_Overall_Posting_Trend.png', dpi=300, bbox_inches='tight')
        plt.show()
        print("Chart generated: 9_Platform_Overall_Posting_Trend.png")
    
    def visualize_brand_ranking(self):
        """Chart 10: Brand post count ranking"""
        if 'frequency' not in self.results:
            return
        
        for platform_key, metrics in self.results['frequency'].items():
            platform_name = 'Weibo' if platform_key == 'weibo' else 'X Platform'
            
            if len(metrics['brands']) > 1:
                plt.figure(figsize=(12, 6))
                brand_totals = []
                
                for brand, daily_posts in metrics['brands_daily'].items():
                    total_posts = daily_posts.sum()
                    brand_totals.append((brand, total_posts))
                
                # Sort by post count
                brand_totals.sort(key=lambda x: x[1], reverse=True)
                brands = [x[0] for x in brand_totals]
                totals = [x[1] for x in brand_totals]
                
                colors = plt.cm.viridis(np.linspace(0, 1, len(brands)))
                bars = plt.bar(brands, totals, color=colors)
                
                # Add values on bars
                for bar, total in zip(bars, totals):
                    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(totals)*0.01, 
                            f'{total}', ha='center', va='bottom', fontsize=9)
                
                plt.title(f'{platform_name} Brand Post Count Ranking', fontsize=16, fontweight='bold')
                plt.xlabel('Brand')
                plt.ylabel('Total Post Count')
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3, axis='y')
                plt.tight_layout()
                plt.savefig(f'{self.output_folder}/10_{platform_name}_Brand_Post_Ranking.png', dpi=300, bbox_inches='tight')
                plt.show()
                print(f"Chart generated: 10_{platform_name}_Brand_Post_Ranking.png")
    
    def visualize_boxplot_distribution(self):
        """Chart 11: Platform posting distribution boxplot"""
        if 'frequency' not in self.results:
            return
        
        plt.figure(figsize=(10, 6))
        post_data = []
        labels = []
        for platform_key, metrics in self.results['frequency'].items():
            platform_name = 'Weibo' if platform_key == 'weibo' else 'X Platform'
            post_data.append(metrics['daily_posts'].values)
            labels.append(platform_name)
        
        plt.boxplot(post_data, labels=labels)
        plt.title('Platform Daily Post Distribution', fontsize=16, fontweight='bold')
        plt.ylabel('Daily Post Count')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/11_Platform_Daily_Post_Distribution.png', dpi=300, bbox_inches='tight')
        plt.show()
        print("Chart generated: 11_Platform_Daily_Post_Distribution.png")
    
    def visualize_moving_average(self):
        """Chart 12: Moving average trend comparison"""
        if 'frequency' not in self.results:
            return
        
        plt.figure(figsize=(15, 8))
        for platform_key, metrics in self.results['frequency'].items():
            platform_name = 'Weibo' if platform_key == 'weibo' else 'X Platform'
            plt.plot(metrics['moving_avg_7d'].index, metrics['moving_avg_7d'].values,
                    label=f'{platform_name} 7-day Moving Average', linewidth=2)
        
        plt.title('Platform Moving Average Trend', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Post Count (7-day Moving Average)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{self.output_folder}/12_Platform_Moving_Average_Trend.png', dpi=300, bbox_inches='tight')
        plt.show()
        print("Chart generated: 12_Platform_Moving_Average_Trend.png")
    
    def generate_all_visualizations(self):
        """Generate all visualization charts"""
        print("\nStarting visualization generation")
        
        # Time pattern charts
        self.visualize_total_posts_comparison()
        self.visualize_daily_posts_comparison()
        self.visualize_peak_hour_distribution()
        self.visualize_platform_distribution()
        self.visualize_weibo_hourly_patterns()
        self.visualize_daily_patterns_comparison()
        self.visualize_account_daily_patterns()
        
        # Frequency charts
        self.visualize_frequency_timeseries()
        self.visualize_platform_comparison()
        self.visualize_brand_ranking()
        self.visualize_boxplot_distribution()
        self.visualize_moving_average()
        
        print("\nAll charts generated")
    
    def export_results_to_csv(self):
    
        # Platform overall statistics
        platform_stats = []
        for platform_key in ['weibo', 'x']:
            if platform_key in self.results.get('frequency', {}):
                metrics = self.results['frequency'][platform_key]
                platform_name = 'Weibo' if platform_key == 'weibo' else 'X_Platform'
                platform_stats.append({
                    'Platform': platform_name,
                    'Total_Posts': metrics['total_posts'],
                    'Brand_Count': metrics['brands_count'],
                    'Analysis_Days': metrics['total_days'],
                    'Avg_Daily_Posts': metrics['posts_per_day'],
                    'Max_Daily_Posts': metrics['max_posts_per_day'],
                    'Min_Daily_Posts': metrics['min_posts_per_day'],
                    'Median_Daily_Posts': metrics['median_posts_per_day'],
                    'Std_Daily_Posts': metrics['std_posts_per_day'],
                    'Start_Date': metrics['date_range'][0].strftime('%Y-%m-%d'),
                    'End_Date': metrics['date_range'][1].strftime('%Y-%m-%d')
                })
        
        if platform_stats:
            pd.DataFrame(platform_stats).to_csv(f'{self.output_folder}/platform_overall_statistics.csv', index=False)
            print("Exported: platform_overall_statistics.csv")
        
        # Brand detailed statistics
        brand_stats = []
        for platform_key in ['weibo', 'x']:
            if platform_key in self.results.get('frequency', {}):
                metrics = self.results['frequency'][platform_key]
                platform_name = 'Weibo' if platform_key == 'weibo' else 'X_Platform'
                for brand, stats in metrics['brands_stats'].items():
                    brand_stats.append({
                        'Platform': platform_name,
                        'Brand': brand,
                        'Total_Posts': stats['total_posts'],
                        'Avg_Daily_Posts': stats['mean_daily'],
                        'Median_Daily_Posts': stats['median_daily'],
                        'Std_Daily_Posts': stats['std_daily'],
                        'Max_Daily_Posts': stats['max_daily'],
                        'Min_Daily_Posts': stats['min_daily'],
                        'Active_Days': stats['active_days'],
                        'Active_Rate_Percent': stats['active_rate']
                    })
        
        if brand_stats:
            pd.DataFrame(brand_stats).to_csv(f'{self.output_folder}/brand_detailed_statistics.csv', index=False)
            print("Exported: brand_detailed_statistics.csv")
        
        # Account level analysis
        if 'account_level' in self.results:
            account_data = []
            for (platform, account_name), stats in self.results['account_level'].items():
                account_data.append({
                    'Platform': platform,
                    'Account_Name': account_name,
                    'Total_Posts': stats['total_posts'],
                    'Analysis_Days': stats['date_range_days'],
                    'Avg_Daily_Posts': stats['avg_daily_posts'],
                    'Peak_Hour': stats['peak_hour'],
                    'Peak_Hour_Count': stats['peak_hour_count'],
                    'Peak_Day': stats['peak_day'],
                    'Peak_Day_Name': stats['peak_day_name'],
                    'Peak_Day_Count': stats['peak_day_count']
                })
            
            pd.DataFrame(account_data).to_csv(f'{self.output_folder}/account_level_analysis.csv', index=False)
            print("Exported: account_level_analysis.csv")
        
        # Daily posting data
        daily_data = []
        for platform_key in ['weibo', 'x']:
            if platform_key in self.results.get('frequency', {}):
                metrics = self.results['frequency'][platform_key]
                platform_name = 'Weibo' if platform_key == 'weibo' else 'X_Platform'
                for i, date in enumerate(metrics['full_date_range']):
                    daily_data.append({
                        'Platform': platform_name,
                        'Date': date.strftime('%Y-%m-%d'),
                        'Total_Posts': metrics['daily_posts'].iloc[i],
                        '7Day_Moving_Avg': metrics['moving_avg_7d'].iloc[i] if i < len(metrics['moving_avg_7d']) else None,
                        '30Day_Moving_Avg': metrics['moving_avg_30d'].iloc[i] if i < len(metrics['moving_avg_30d']) else None
                    })
        
        if daily_data:
            pd.DataFrame(daily_data).to_csv(f'{self.output_folder}/daily_posting_data.csv', index=False)
            print("Exported: daily_posting_data.csv")
        
        print(f"\nAll data exported")
    
    def generate_analysis_report(self):
        print("\nAnalysis Report")
        
        print("\nPlatform Overall Statistcs:")
        
        for platform_key in ['weibo', 'x']:
            if platform_key in self.results.get('frequency', {}):
                metrics = self.results['frequency'][platform_key]
                platform_name = 'Weibo' if platform_key == 'weibo' else 'X'
                
                print(f"\n{platform_name}:")
                print(f"Total Posts: {metrics['total_posts']:,}")
                print(f"Brand Count: {metrics['brands_count']}")
                print(f"Analysis Period: {metrics['total_days']} days")
                print(f"Average Daily Posts: {metrics['posts_per_day']:.2f}")
                print(f"Maximum Daily Posts: {metrics['max_posts_per_day']}")
                print(f"Minimum Daily Posts: {metrics['min_posts_per_day']}")
                print(f"Standard Deviation: {metrics['std_posts_per_day']:.2f}")
                print(f"Time Range: {metrics['date_range'][0].strftime('%Y-%m-%d')} to {metrics['date_range'][1].strftime('%Y-%m-%d')}")

        print("\nBrand Performance Analysis:")
        
        for platform_key in ['weibo', 'x']:
            if platform_key in self.results.get('frequency', {}):
                metrics = self.results['frequency'][platform_key]
                platform_name = 'Weibo' if platform_key == 'weibo' else 'X'
                
                print(f"\n{platform_name} Brand Ranking:")
                brand_totals = [(brand, stats['total_posts']) for brand, stats in metrics['brands_stats'].items()]
                brand_totals.sort(key=lambda x: x[1], reverse=True)
                
                for i, (brand, total) in enumerate(brand_totals, 1):
                    stats = metrics['brands_stats'][brand]
                    print(f"{i}. {brand}: {total:,} posts "
                          f"(Avg: {stats['mean_daily']:.2f}/day, "
                          f"Active: {stats['active_rate']:.1f}%)")

        if 'account_level' in self.results:
            print("\nAccount Level Insights:")
            
            for (platform, account_name), stats in self.results['account_level'].items():
                print(f"\n{platform} - {account_name}:")
                print(f"Total Posts: {stats['total_posts']:,}")
                print(f"Average Daily Posts: {stats['avg_daily_posts']:.2f}")
                if platform == 'Weibo' and stats['peak_hour'] != -1:
                    print(f"Peak Posting Hour: {stats['peak_hour']}:00 ({stats['peak_hour_count']} posts)")
                print(f"Peak Posting Day: {stats['peak_day_name']} ({stats['peak_day_count']} posts)")
 
        print("\nReport Summary:")
        
        total_accounts = len(self.results.get('account_level', {}))
        total_posts = sum([metrics['total_posts'] for metrics in self.results.get('frequency', {}).values()])
        total_brands = sum([metrics['brands_count'] for metrics in self.results.get('frequency', {}).values()])
        
        print(f"Total Accounts Analyzed: {total_accounts}")
        print(f"Total Brands Analyzed: {total_brands}")
        print(f"Total Posts Analyzed: {total_posts:,}")
        print(f"Analysis Period: Varies by platform")
        print(f"Output Files: {len(os.listdir(self.output_folder))} files generated")

def main():
    """Main execution function"""
    print("Starting Analysis")
    
    # Initialize analyzer
    analyzer = Analyzer(output_folder='./social_media_analysis_results')
    
    # Load data
    print("\nLoading data files")
    
    weibo_folder = "./weibo_data"
    x_folder = "./x_data"
    
    combined_data = analyzer.combine_all_data(weibo_folder, x_folder)
    
    if combined_data is None:
        print("Data loading failed")
        return
    
    print(f"\nData loading completed")
    print(f"Total records: {len(combined_data):,}")
    print(f"Weibo accounts: {len(analyzer.weibo_data_all)}")
    print(f"X ccounts: {len(analyzer.x_data_all)}")

    print("\nTime pattern analysis")
    analyzer.analyze_account_level_patterns()
    
    print("\nFrequency pattern analysis")
    analyzer.analyze_frequency_patterns()

    print("\nGenerating visualizations")
    analyzer.generate_all_visualizations()

    print("\nExporting results")
    analyzer.export_results_to_csv()

    analyzer.generate_analysis_report()
    
    print(f"\nAnalysis completed")

if __name__ == "__main__":
    main()
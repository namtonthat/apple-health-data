# Automate run every day
# adjust schedule using crontab -e
conda activate apple-health
cd ~/Documents/scratch/apple-health-calendar
export AWS_DEFAULT_PROFILE=personal
python3 apple-health.py

#!/usr/bin/env python3
"""Regression tests for extracted idle-timer and charger diagnostic code."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
def extract(s,n):
 a=s.index(n+'(');a=s.rfind('\n',0,a)+1;return s[a:s.index('\n}',a)+2]
s=(r/'kernel/sched/cpufreq_schedutil.c').read_text()
base='''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
'''
cpu=base+'''
typedef long long s64;
static s64 sleep_ns;
static s64 tick_nohz_get_sleep_length(void) {return sleep_ns;}
static s64 ktime_to_ms(s64 v) {return v/1000000;}
static s64 ktime_to_us(s64 v) {return v/1000;}
struct sugov_cpu {unsigned long util;};
struct sugov_exynos {unsigned long min;int expired_time;};
static struct sugov_cpu sugov_cpu={101};
static struct sugov_exynos sugov_exynos={100,70};
#define per_cpu(n,c) (n)
static int boosted;
static int schedtune_cpu_boost(unsigned int cpu) {return boosted;}
'''+extract(s,'get_next_event_time_ms')+'\n'+extract(s,'sugov_need_slack_timer')+'''
int main(void) {
 long durations[]={0,1,69,70,71,1000};
 for(unsigned i=0;i<sizeof(durations)/sizeof(durations[0]);i++) {
  sleep_ns=durations[i]*1000000LL;
  assert(sugov_need_slack_timer(0)==(durations[i]>70));
 }
 sleep_ns=1000000000LL;boosted=1;assert(!sugov_need_slack_timer(0));
 boosted=0;sugov_cpu.util=100;assert(!sugov_need_slack_timer(0));
 return 0;
}
'''
s=(r/'drivers/battery_v2/max77705_charger.c').read_text()
a=s.index('\t\tcase POWER_SUPPLY_EXT_PROP_MONITOR_WORK:');b=s.index('\n\t\tdefault:',a)
block=s[a:b]
charger=base+'''
typedef uint8_t u8;typedef uint32_t u32;
struct max77705_charger_data {void *i2c;int otg_on;};
static bool monitor_debug;static int reads;
#define READ_ONCE(v) (v)
#define POWER_SUPPLY_EXT_PROP_MONITOR_WORK 1
#define MAX77705_CHG_REG_CNFG_00 0xb7
#define MAX77705_CHG_REG_CNFG_05 0xbc
#define CHG_CNFG_00_MODE_MASK 15
#define CHG_CNFG_00_MODE_SHIFT 0
#define CHG_CNFG_05_REG_B2SOVRC_MASK 15
#define CHG_CNFG_05_REG_B2SOVRC_SHIFT 0
#define pr_info(...) ((void)0)
static int max77705_read_reg(void *i,unsigned int addr,u8 *v) {reads++;*v=0;return 0;}
'''+extract(s,'max77705_test_read')+'\n'+extract(s,'max77705_chg_monitor_work')+'''
static void monitor(struct max77705_charger_data *charger) {
 switch(POWER_SUPPLY_EXT_PROP_MONITOR_WORK) {
'''+block+'''
 }
}
int main(void) {
 struct max77705_charger_data c={0};
 monitor_debug=false;monitor(&c);assert(reads==0);
 monitor_debug=true;monitor(&c);assert(reads==21);
 monitor_debug=false;reads=0;max77705_test_read(&c);assert(reads==19);
 return 0;
}
'''

s=(r/'drivers/gpu/arm/exynos/frontend/gpex_dvfs.c').read_text()
gpu=base+'''
static struct {bool timer_active;int spinlock,dvfs_work;void *dvfs_wq;} dvfs;
static bool locked;static int synced,destroyed;
#define spin_lock_irqsave(l,f) do { assert(!locked);locked=true;(f)=0; } while(0)
#define spin_unlock_irqrestore(l,f) do { assert(locked);locked=false; } while(0)
static void cancel_delayed_work_sync(int *w) {
 assert(!locked);assert(!dvfs.timer_active);synced++;
}
static void destroy_workqueue(void *q) {assert(synced && !dvfs.timer_active);destroyed++;}
'''+extract(s,'gpu_dvfs_cancel_work')+'\n'+extract(s,'gpu_pm_metrics_term')+'''
int main(void) {
 dvfs.timer_active=true;gpu_dvfs_cancel_work();assert(!dvfs.timer_active && synced==1);
 dvfs.timer_active=true;gpu_pm_metrics_term();assert(!dvfs.timer_active && synced==2 && destroyed==1);
 return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='f22r-optimization-tests-') as d:
 for name,code in [('idle-timer-units',cpu),('charger-diagnostics',charger),('gpu-poll-stop-order',gpu)]:
  p=Path(d)/name;p.with_suffix('.c').write_text(code)
  subprocess.run(['cc','-std=gnu11','-O1','-fsanitize=address,undefined',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  subprocess.run([str(p)],check=True);print('PASS '+name)
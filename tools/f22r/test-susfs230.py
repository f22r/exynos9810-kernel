#!/usr/bin/env python3
"""Host regression tests for extracted SUSFS functions; not a device test."""
from pathlib import Path
import subprocess, tempfile, sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]
src=(root/'fs/susfs.c').read_text()
def function(text,name):
 a=text.index(name+'('); a=text.rfind('\n',0,a)+1; b=text.index('\n}',a)+2
 return text[a:b]
common='''#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#define __user
#define SUSFS_LOGI(...) ((void)0)
#define SUSFS_LOGE(...) ((void)0)
'''
cases={}
cases['hash-collision']=common+'''
struct st_susfs_sus_kstat_hlist { unsigned long target_ino; dev_t target_dev; int spoofed_mnt_id;
 struct { unsigned long spoofed_ino; dev_t spoofed_dev; } info; };
static struct st_susfs_sus_kstat_hlist entries[2];
#define rcu_read_lock() ((void)0)
#define rcu_read_unlock() ((void)0)
/* Both records are deliberately exposed as the same hash bucket. */
#define hash_for_each_possible_rcu(t,e,n,k) for(int i=0;i<2 && ((e)=&entries[i],1);i++)
'''+function(src,'susfs_sus_kstat_spoof_inotify_fdinfo')+'\n'+function(src,'susfs_sus_kstat_spoof_proc_fd_seq_show')+'''
int main(void) {
 entries[0]=(struct st_susfs_sus_kstat_hlist){.target_ino=11,.target_dev=7,.spoofed_mnt_id=88,.info={111,9}};
 entries[1]=(struct st_susfs_sus_kstat_hlist){.target_ino=22,.target_dev=7,.spoofed_mnt_id=99,.info={222,10}};
 unsigned long ino=22;dev_t dev=7;int mount=0;
 susfs_sus_kstat_spoof_inotify_fdinfo(&ino,&dev);assert(ino==222 && dev==10);
 ino=22;susfs_sus_kstat_spoof_proc_fd_seq_show(&mount,&ino,7);assert(mount==99 && ino==222);
 ino=33;dev=7;susfs_sus_kstat_spoof_inotify_fdinfo(&ino,&dev);assert(ino==33 && dev==7);
 ino=22;dev=8;susfs_sus_kstat_spoof_inotify_fdinfo(&ino,&dev);assert(ino==22 && dev==8);
 return 0;
}
'''
cases['feature-buffer-oom']=common+'''
#define GFP_KERNEL 0
#define SUSFS_ENABLED_FEATURES_SIZE 8192
struct st_susfs_enabled_features { char enabled_features[8192]; int err; };
static int fail_alloc,freed;
static void *kzalloc(size_t n,int f) {return fail_alloc ? NULL : calloc(1,n);}
static void kfree(void *p) {freed++;free(p);}
static int copy_to_user(void *d,const void *s,size_t n) {assert(d && s);memcpy(d,s,n);return 0;}
#define copy_from_user copy_to_user
'''+function(src,'susfs_get_enabled_features')+'''
int main(void) {
 struct st_susfs_enabled_features reply={0};void *ptr=&reply;
 fail_alloc=1;susfs_get_enabled_features(&ptr);assert(reply.err==-ENOMEM && freed==0);
 fail_alloc=0;susfs_get_enabled_features(&ptr);assert(reply.err==0 && freed==1);
 return 0;
}
'''
bridge=(root/'KernelSU-Next/kernel/feature/susfs_bridge.c').read_text()
cases['root-domain-dispatch']=common+'''
#define CMD_SUSFS_ENABLE_AVC_LOG_SPOOFING 1
#define CMD_SUSFS_SHOW_ENABLED_FEATURES 2
#define CMD_SUSFS_SHOW_VARIANT 3
#define CMD_SUSFS_SHOW_VERSION 4
static unsigned uid;static bool domain;static int called;
struct fake_uid {unsigned val;};
static struct fake_uid current_uid(void) {return (struct fake_uid){uid};}
static bool is_ksu_domain(void) {return domain;}
#define susfs_set_avc_log_spoofing(a) (++called)
#define susfs_get_enabled_features(a) (++called)
#define susfs_show_variant(a) (++called)
#define susfs_show_version(a) (++called)
'''+function(bridge,'f22r_susfs_command')+'''
int main(void) {
 void *arg=NULL;uid=10000;domain=true;
 assert(f22r_susfs_command(4,&arg)==-EPERM && !called);
 uid=0;domain=false;assert(f22r_susfs_command(4,&arg)==-EPERM && !called);
 domain=true;assert(f22r_susfs_command(4,&arg)==0 && called==1);
 assert(f22r_susfs_command(999,&arg)==-EOPNOTSUPP && called==1);
 return 0;
}
'''
stat=(root/'fs/statfs.c').read_text()
cases['statfs-fallback']=common+'''
struct inode {int unused;};struct kstatfs {long f_frsize,f_bsize;};
struct dentry;
struct super_operations {int (*statfs)(struct dentry*,struct kstatfs*);};
struct super_block {struct super_operations *s_op;};
struct dentry {struct super_block *d_sb;struct inode inode;};
#define d_backing_inode(d) (&(d)->inode)
static int security_error,spoof_error,real_calls;
static int security_sb_statfs(struct dentry*d) {return security_error;}
static int susfs_sus_kstat_spoof_vfs_statfs(struct inode*i,struct kstatfs*b,bool*f) {b->f_bsize=123;return spoof_error;}
static int real_stat(struct dentry*d,struct kstatfs*b) {real_calls++;b->f_bsize=456;return 0;}
'''+function(stat,'susfs_statfs_by_dentry')+'''
int main(void) {
 struct super_operations ops={real_stat};struct super_block sb={&ops};struct dentry d={.d_sb=&sb};
 struct kstatfs out={0};bool fuse=false;
 assert(susfs_statfs_by_dentry(&d,&out,&fuse)==0 && out.f_bsize==123 && real_calls==0);
 spoof_error=-EINVAL;assert(susfs_statfs_by_dentry(&d,&out,&fuse)==0 && out.f_bsize==456 && real_calls==1);
 security_error=-EACCES;assert(susfs_statfs_by_dentry(&d,&out,&fuse)==-EACCES && real_calls==1);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='f22r-susfs-tests-') as tmp:
 for name,code in cases.items():
  p=Path(tmp)/name;p.with_suffix('.c').write_text(code)
  subprocess.run(['cc','-std=gnu11','-O1','-fsanitize=undefined,address','-g',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  subprocess.run([str(p)],check=True)
  print('PASS '+name)
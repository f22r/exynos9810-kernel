"""Compile actual kernel payload preparation and allocators with host uaccess mocks.

No phone access: this tests ABI decoding/error bounds, not live SELinux enforcement.
"""
import pathlib, subprocess, sys, tempfile
root = pathlib.Path(sys.argv[1])
rules = (root / 'kernel/selinux/rules.c').read_text()
header = (root / 'kernel/compat/kernel_compat.h').read_text()
compat = (root / 'kernel/compat/kernel_compat.c').read_text()
def function(text, signature):
    start = text.index(signature)
    pos = text.index('{', start)
    depth = 1
    end = pos + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]
preamble = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef uint8_t u8; typedef uint32_t u32; typedef uint64_t u64;
typedef unsigned int gfp_t;
#define __user
#define CONFIG_ARM64 1
#define KERNEL_VERSION(a,b,c) ((a)*65536+(b)*256+(c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4,9,337)
#define GFP_KERNEL 3
#define GFP_ATOMIC 4
#define GFP_NOIO 1
#define __GFP_DIRECT_RECLAIM 1
#define __GFP_ZERO 8
#define __GFP_NOWARN 16
#define PAGE_SIZE 4096
#define KSU_SEPOLICY_MAX_BATCH_SIZE (1024*1024)
#define KSU_SEPOLICY_MAX_ARGS 7
static int fail_alloc, vm_calls, last_flags;
static void *kmalloc(size_t n, gfp_t f) {last_flags=f; return fail_alloc ? NULL : malloc(n);}
static void *vmalloc(size_t n) {vm_calls++; return malloc(n);}
static void *vzalloc(size_t n) {vm_calls++; return calloc(1,n);}
#define kfree(p) free((void *)(p))
#define kvfree free
static int atomic_context, irq_off, freed, deferred;
static char vm_marker;
#define is_vmalloc_addr(p) ((p) == &vm_marker)
#define in_atomic() atomic_context
#define irqs_disabled() irq_off
#define vfree(p) (++freed)
#define vfree_atomic(p) (++deferred)
static int copy_from_user(void *d, const void *s, size_t n) {
 if ((uintptr_t)s < 4096) return 1; memcpy(d,s,n); return 0;
}
static long strncpy_from_user(char *d, const char *s, long n) {
 if ((uintptr_t)s < 4096) return -EFAULT;
 size_t len = strnlen(s,n); memcpy(d,s,len); if (len < n) d[len]=0; return len;
}
struct sepol_data {u32 cmd, subcmd;};
static int sepol_expected_argc(u32 c) {
 const int n[]={0,4,5,1,2,2,1,5,4,3}; return c>0 && c<10 ? n[c] : -EINVAL;
}
'''
allocators = function(header, 'static inline void *ksu_kvmalloc') + '\n' + function(compat, 'static void *__kvmalloc')
allocators += '\n' + function(header, 'static inline void ksu_kvfree')
helper = ''
if 'static int sepol_copy_legacy_payload' in rules:
    helper = function(rules, 'static int sepol_copy_legacy_payload')
handle = rules[rules.rindex('int handle_sepolicy(void __user *user_data, u64 data_len)'):]
prepare = handle[handle.index('\tif (!user_data'):handle.index('\tif (!getenforce())')]
main = r'''
static int prepare(void *user_data, u64 data_len, u8 **result, u64 *length) {
 u8 *payload; int ret=0;
 PREPARATION
 *result=payload; *length=data_len; return 0;
out_free: free(payload); return ret;
}
int main(int argc, char **argv) {
 if (argc>1 && !strcmp(argv[1], "alloc")) {
   ksu_kvfree(&vm_marker); assert(freed==1 && deferred==0);
   atomic_context=1; ksu_kvfree(&vm_marker); atomic_context=0;
   irq_off=1; ksu_kvfree(&vm_marker); irq_off=0;
   assert(freed==1 && deferred==2);
   ksu_kvfree(malloc(16)); assert(freed==1 && deferred==2);
   fail_alloc=1; vm_calls=0;
   assert(ksu_kvmalloc(64,GFP_ATOMIC)==NULL); assert(vm_calls==0);
   assert(__kvmalloc(64,GFP_ATOMIC)==NULL); assert(vm_calls==0);
   assert(!(last_flags & __GFP_DIRECT_RECLAIM));
   void *p=ksu_kvmalloc(64,GFP_KERNEL|__GFP_ZERO); assert(p && vm_calls==1);
   for (int i=0;i<64;i++) assert(((char*)p)[i]==0); free(p);
   puts("PASS atomic allocation and deferred free; sleeping zero allocation preserved"); return 0;
 }
 struct {u32 cmd, subcmd; u64 args[7];} old={1,1,{0}};
 const char *args[]={"zygote","zygote","process","execmem"};
 for(int i=0;i<4;i++) old.args[i]=(uintptr_t)args[i];
 u8 *payload=NULL; u64 length=0;
 assert(prepare(&old,0,&payload,&length)==0);
 assert(length==8+4*5+6+6+7+7); assert(!memcmp(payload,&old,8));
 size_t offset=8;
 for(int i=0;i<4;i++) {u32 n; memcpy(&n,payload+offset,4); offset+=4;
 assert(n==strlen(args[i])); assert(!strcmp((char*)payload+offset,args[i])); offset+=n+1;}
 u8 *modern=NULL; u64 modern_len=0;
 assert(prepare(payload,length,&modern,&modern_len)==0);
 assert(modern_len==length && !memcmp(payload,modern,length)); free(modern); free(payload);
 old.args[0]=0; assert(prepare(&old,0,&payload,&length)==0);
 assert(!memcmp(payload+8,"\0\0\0\0\0",5)); free(payload);
 old.args[0]=1; assert(prepare(&old,0,&payload,&length)==-EFAULT);
 char longstr[129]; memset(longstr,'x',128); longstr[128]=0;
 old.args[0]=(uintptr_t)longstr; assert(prepare(&old,0,&payload,&length)==-E2BIG);
 longstr[127]=0; assert(prepare(&old,0,&payload,&length)==0); free(payload);
 old.cmd=99; assert(prepare(&old,0,&payload,&length)==-EINVAL);
 assert(prepare((void*)1,0,&payload,&length)==-EFAULT);
 assert(prepare(NULL,0,&payload,&length)==-EINVAL);
 assert(prepare(&old,KSU_SEPOLICY_MAX_BATCH_SIZE+1,&payload,&length)==-E2BIG);
 fail_alloc=1; old.cmd=1; assert(prepare(&old,0,&payload,&length)==-ENOMEM);
 puts("PASS legacy ABI, wildcard, modern payload, bad pointer, length and OOM cases");
}
'''.replace('PREPARATION', prepare)
with tempfile.TemporaryDirectory() as td:
    c = pathlib.Path(td)/'test.c'
    c.write_text(preamble + allocators + '\n#define kvmalloc ksu_kvmalloc\n' + helper + main)
    exe = str(pathlib.Path(td)/'test')
    subprocess.run(['cc','-std=gnu11','-g','-fsanitize=address,undefined',str(c),'-o',exe],check=True)
    failures=0
    for mode in ['alloc','abi']:
        result=subprocess.run([exe,mode])
        failures += result.returncode != 0
    sys.exit(bool(failures))

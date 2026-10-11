#if !defined(__IP_H__)
#define __IP_H__

#include "std_basal.h"
#include "std.h"

typedef void  (*Fun)(void *);

#define IPCALL(IP)  (IP.fun(&IP))


#define TRUE   0xEB
#define FALSE  0x00

#define FLT32_ZERO 1.0E-6

#define ABS(a)    (((a) > 0) ? (a) : -(a))
#define MIN(a, b) (((a) > (b)) ? (b) : (a))

#define SAM_DAMP    0x00    /* SAM速率阻尼方式 */
#define SAM_PITCH   0x11    /* SAM俯仰搜索方式 */
#define SAM_ROLL    0x22    /* SAM滚动搜索方式 */
#define SAM_CRUISE  0x33    /* SAM巡航方式 */
#define NOCTRL      0x44    /* 不控 */

#endif // __IP_H__

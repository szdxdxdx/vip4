#if !defined(__PSEUDORATE_H__)
#define __PSEUDORATE_H__

#include "IP.h"

void PseudoRateFun(void *p);

/* 数字伪速率调制器 */
typedef struct __PseudoRate {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    float32 *pu;   /* u数组指针 */

    /* 输出端口 */
    unint08 Yp[3]; /* 脉冲方向输出 */
    unint08 Yn[3]; /* 脉冲方向输出 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    float32 r[3]; /* 反馈信号 */

    /* 参数变量 */
    float32 h1[3]; /* 开坎值 */
} PseudoRate;

#endif // __PSEUDORATE_H__

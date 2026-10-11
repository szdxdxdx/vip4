#if !defined(__GYROSTATESET_H__)
#define __GYROSTATESET_H__

#include "IP.h"

void GyroStateSetFun(void *p);

/* 陀螺状态收集 */
typedef struct __GyroStateSet {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    unint32 powerState;  /* 陀螺加电状态 */
    unint32 healthState; /* 陀螺健康状态 */

    /* 输出端口 */
    unint08 StateFlag[9]; /* 陀螺可用标志 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    /* 无 */
} GyroStateSet;

#endif // __GYROSTATESET_H__

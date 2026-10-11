#if !defined(__GYROANGCAL_H__)
#define __GYROANGCAL_H__

#include "IP.h"

void GyroAngCalFun(void *p);

/* 陀螺角度积分 */
typedef struct __GyroAngCal {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    float32 *W;

    /* 输出端口 */
    float32 Gi[3]; /* 陀螺角度积分 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    float32 ctlPeriod; /* 控制周期（s） */

} GyroAngCal;

#endif // __GYROANGCAL_H__

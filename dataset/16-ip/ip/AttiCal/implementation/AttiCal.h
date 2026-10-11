#if !defined(__ATTICAL_H__)
#define __ATTICAL_H__

#include "IP.h"

void AttiCalFun(void *p);

/* 姿态确定 */
typedef struct __AttiCal {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    unint32 workmode; /* 当前模式 */
    unint08 flgSP;    /* 见太阳标志 */
    float32 royaw;    /* 太敏滚动角 */
    float32 piyaw;    /* 太敏俯仰角 */
    float32 *W;       /* 陀螺算出的角速度数组指针 */

    /* 输出端口 */
    float32 angle[3]; /* 三轴姿态角 */
    float32 rate[3];  /* 三轴角速度 */

    /* 输入输出端口 */
    float32 *Gi; /* 陀螺角度积分数组指针 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    /* 无 */
} AttiCal;

#endif // __ATTICAL_H__

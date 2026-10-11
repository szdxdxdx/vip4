#if !defined(__THRUSTERCTRLLOGIC_H__)
#define __THRUSTERCTRLLOGIC_H__

#include "IP.h"

void ThrusterCtrlLogicFun(void *p);

/* 推力器组合逻辑 */
typedef struct __ThrusterCtrlLogic {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    unint08 *Yp; /* 脉冲方向输出数组指针（正方向） */
    unint08 *Yn; /* 脉冲方向输出数组指针（负方向） */

    /* 输出端口 */
    unint08 wPulse; /* 推力器组合 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    /* 无 */
} ThrusterCtrlLogic;

#endif // __THRUSTERCTRLLOGIC_H__

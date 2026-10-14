#if !defined(__CS_STARTIMENEXTCALC_H__)
#define __CS_STARTIMENEXTCALC_H__

#include "../../IP.h"

// 函数声明
void CS_StarTimeNextCalcFun(void *p);

// IP 结构体定义
typedef struct __CS_StarTimeNextCalc
{
    /* 函数接口 */
    Fun fun;
    float64 m_starTime;                         /* 当前星时 t */
    float64 m_DeltaT;                           /* 控制周期 */
    /* 输出变量 */
    /* 输入输出变量 */
    float64 m_starTime_Next;                    /* 下周期星时 t_next */
    /* 输入变量 */
    unint32 csOrbDataOther_F_DTOrbitEUpdate;    /* */
    /* 状态变量*/
    /* 参数变量 */
} CS_StarTimeNextCalc;

#endif // __CS_STARTIMENEXTCALC_H__
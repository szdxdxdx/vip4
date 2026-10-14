#if !defined(__CS_CLEARCTRL__)
#define __CS_CLEARCTRL__

#include "../../IP.h"

void CS_ClearCtrlFun(void *p);

/* 模式切换指令处理 */
typedef struct __CS_ClearCtrl
{
    /* 接口函数 */
    Fun     fun;
    /* 输入端口 */

    /* 输出端口 */
    float64 csJPCData_mPhaseT[3];   /* 喷气脉宽,s       t_axis */
    float64 csJPCData_t[12];        /* Thr[i].t 各姿控喷管本拍输出喷气脉宽 */

    /* 输入输出端口 */

    /* 状态变量 */
    /* 参数变量 */
} CS_ClearCtrl;

#endif // __CS_CLEARCTRL__

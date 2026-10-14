#if !defined(__MODEINIT_NWM_H__)
#define __MODEINIT_NWM_H__

#include "../../IP.h"

void ModeInit_NWMFun(void *p);

/* 模式切换指令处理 */
typedef struct __ModeInit_NWM
{
    /* 接口函数*/
    Fun     fun;
    /* 输入端口*/
    /* 输出端口 */
    float64 csMnvData_A_Trgt[3];              /* 目标姿态 */
    /* 输入输出端口 */
    /* 状态变量 */
    /* 参数变量 */
} ModeInit_NWM;

#endif // __MODEINIT_NWM_H__
#if !defined(__MODECONVERT_EIM_H__)
#define __MODECONVERT_EIM_H__

#include "../IP.h"

void ModeConvert_EIMFun(void *p);

/* 模式切换指令处理 */
typedef struct __ModeConvert_EIM
{
    /* 接口函数 */
    Fun     fun;

    /* 输入端口 */
    float64 ModeObject_Timer_Mode[14];          /* 模式执行时间 */

    /* 输出端口 */

    /* 输入输出端口 */
    unint32 m_WorkMode;                         /* 当前模式 */

    /* 状态变量 */

    /* 参数变量 */
    float64 csModePara_dt_END_EIM;              /* 相对入轨段计时开始的入轨段结束时间（无红外时设置为120） */

} ModeConvert_EIM;

#endif // __MODECONVERT_EIM_H__
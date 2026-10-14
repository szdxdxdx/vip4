#if !defined(__CS_GYRODATA_DISPOSAL__)
#define __CS_GYRODATA_DISPOSAL__

#include "../../IP.h"

void CS_GyroData_DisposalFun(void *p);

typedef struct __CS_GyroData_Disposal
{
    /* 接口函数 */
    // Fun     fun;

    /* 输入端口 */
//    unint32 csGyroDiagData_F_NoUseGroup;        /* 本周期无定姿陀螺组标志 */
//    unint32 csAttPara_FS_AttD;                  /* 定姿方式标志 0 红外陀螺 1 星敏陀螺 2 星敏无陀螺(陀螺开) 3 星敏无陀螺(陀螺关) 4 红外无陀螺(陀螺关) */
//    unint32 csGyroDiagPara_FP_ModeStopCtrl[14]; /* 是否无陀螺组可用时停控(0: 不允许,1: 允许) */
//    unint32 csGyroDiagData_FU_ing[9];           /* 当前陀螺使用标志(0:不使用，1:使用) */
//    float64 csGyroData_deltagm[9];              /* 陀螺i测量角度增量 弧度 */
//    unint32 m_WorkMode;                         /* 当前模式 */

    /* 输出端口 */
//    float64 csGyroData_deltag[3];               /* 陀螺测量得到的星体三轴输出 */
//    float64 csGyroData_wbi[3];                  /* 陀螺测量得到的星体三轴惯性角速度 */
//    unint32 csModeData_F_StopCtrl;              /* 星上停控标志 */

    /* 输入输出端口 */

    /* 状态变量 */
    float64 csGyroData_deltag_Lst[3];           /* 陀螺测量得到的星体三轴输出历史值 */

    /* 参数变量 */
//    float64 csGyroPara_Mlfw;                    /* 惯性角速度限幅 */
//    float64 csGyroPara_Vbs[9][3];               /* 标定后引入闭环的陀螺安装向量 */

} CS_GyroData_Disposal;

#endif //__CS_GYRODATA_DISPOSAL__

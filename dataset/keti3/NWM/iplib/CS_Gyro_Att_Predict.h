#if !defined(__CS_GYRO_ATT_PREDICT__)
#define __CS_GYRO_ATT_PREDICT__

#include "../IP.h"

void    CS_Gyro_Att_PredictFun(void *p);

/* 模式切换指令处理 */
typedef struct __CS_Gyro_Att_Predict
{
    /* 接口函数 */
    Fun     fun;

    /* 输入端口 */
    float64 csGyroData_deltag[3];           /* 陀螺测量得到的星体三轴输出 */
    float64 csGyroData_D0_ESCorr[3];        /* 地敏估陀螺本体系三轴常值漂移 rad/h */
    float64 csGyroData_De_ESCorr[3];        /* 地敏估陀螺本体系三轴指数漂移项 rad/h */
    float64 csOrbData_w0i[3];               /* 考虑轨道进动的轨道系相对于惯性系J2000.0的角速度 */
    unint32 m_WorkMode;                     /* 当前模式 */
    unint32 csAttPara_Seq_AttD[14];         /* 定姿转序（目前支持六种情况，132，123，231，213，312，321） */

    /* 输出端口 */
    float64 csAttCoreData_wbo_ESG[3];       /* 红外陀螺确定本体相对轨道系的惯性角速度 */
    float64 csAttCoreData_Cbo_ESG[3][3];    /* 红外陀螺估计的方向余弦阵(从轨道坐标系到本体坐标系) */
    float64 csAttCoreData_Rate_ESG[3];      /* 星体三轴姿态(红外+陀螺) */
    float64 csAttCoreData_w_ESG[3];         /* 星体惯性角速度(红外陀螺) [ωx_ESG, ωy_ESG, ωz_ESG] */

    /* 输入输出端口 */
    float64 csAttCoreData_A_ESG[3];         /* 星体三轴姿态(红外+陀螺) */

    /* 状态变量 */

    /* 参数变量 */
    float64 csGyroPara_Mlfw;                /* 惯性角速度限幅 */
    float64 csGyroPara_MlfA_ESG[3][14];     /* 姿态估计的角度限幅阈值 */
    float64 m_DeltaT;                       /* 控制周期 */

} CS_Gyro_Att_Predict;

#endif // __CS_GYRO_ATT_PREDICT__
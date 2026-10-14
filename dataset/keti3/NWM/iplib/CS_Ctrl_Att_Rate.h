#if !defined(__CS_CTRL_ATT_RATE_H__)
#define __CS_CTRL_ATT_RATE_H__

#include "../IP.h"

// 函数声明
void CS_Ctrl_Att_RateFun(void *p);

// IP 结构体定义
typedef struct __CS_Ctrl_Att_Rate
{
    /* 函数接口 */
    Fun     fun ;

    /* 输入变量 */
    unint32 m_WorkMode;                                /* 当前模式 */
    unint32 csCtrlerOtherPara_FS_ModeProc[14];         /* 模式处理标志 */
    float64 csSGAttAcqData_A[3];                       /* 姿态角 φ_AAM, θ_AAM, ψ_AAM A_AAM */
    float64 csSGAttAcqData_dA[3];                      /* 姿态角速度 dφ_AAM, dθ_AAM, dψ_AAM */
    float64 csSGAttAcqData_w[3];                       /* 惯性角速度 ωx_AAM、ωy_AAM、ωz_AAM w_AAM */
    unint32 csAttPara_FS_AttD;                         /* 定姿方式标志 0 红外陀螺 1 星敏陀螺 2 星敏无陀螺(陀螺开) 3 星敏无陀螺(陀螺关) 4 红外无陀螺(陀螺关) */
    float64 csAttCoreData_q_STDyn[4];                  /* 惯性姿态四元数(星敏无陀螺) */
    float64 csAttCoreData_w_STDyn[3];                  /* 星体惯性角速度(星敏无陀螺) [ωx_STDyn,ωy_STDyn,ωz_STDyn] */
    float64 csIresData_phi;                            /* 由红外输出计算得到的滚动角 */
    float64 csIresData_theta;                          /* 由红外输出计算得到的俯仰角 */
    float64 csMnvData_A_Ref[3];                        /* 三轴实时目标姿态 */
    unint32 csAttPara_Seq_AttD[14];                    /* 定姿转序（目前支持六种情况，132，123，231，213，312，321） */
    float64 csAttCoreData_Rate_ESG[3];                 /* 星体三轴姿态角速度(红外+陀螺) */
    float64 csAttCoreData_wbo_ESG[3];                  /* 红外陀螺确定本体相对轨道系的惯性角速度 */
    float64 csOrbData_w0i[3];                          /* 考虑轨道进动的轨道系相对于惯性系J2000.0的角速度 */
    unint32 csCtrlerOtherPara_FP_BMC;                  /* 允许偏置动量控制标志 需要单独处理上行注入，放在最后 */
    float64 csAttCoreData_qri[4];                      /* 参考系相对惯性系的目标姿态四元数                           */
    float64 csAttCoreData_wri[3];                      /* 三轴实时目标惯性角速度                                     */
    float64 csOrbData_coi[3][3];                       /* 从惯性系到轨道系的姿态转移矩阵 */
    float64 csAttCoreData_w_ESG[3];                    /* 星体惯性角速度(红外陀螺) [ωx_ESG, ωy_ESG, ωz_ESG] */
    unint32 csCtrlerOtherPara_FP_Qctrl[14];            /* 四元数控制标志 */
    float64 csMnvData_dA_Ref[3];                       /* 三轴实时目标姿态角速度 */
    float64 csAttCoreData_A_STG[3];                    /* 星体三轴姿态(星敏+陀螺)                      */
    float64 csAttCoreData_Rate_STG[3];                 /* 星体三轴姿态角速度(星敏+陀螺)                */
    float64 csAttCoreData_wbo_STG[3];                  /* 星敏陀螺确定本体相对轨道系的惯性角速度 */
    float64 csAttCoreData_Cbo_STG[3][3];               /* 星敏陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系）     */
    float64 csAttCoreData_A_STDyn[3];                  /* 星体三轴姿态(星敏+陀螺)                      */
    float64 csAttCoreData_Rate_STDyn[3];               /* 星体三轴姿态角速度(星敏+陀螺)                */
    float64 csAttCoreData_wbo_STDyn[3];                /* 星敏陀螺确定本体相对轨道系的惯性角速度 */
    float64 csAttCoreData_Cbo_STDyn[3][3];             /* 星敏无陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系）     */
    float64 csIresData_dPhi;                           /* 由红外测量计算的滚动角速度 */
    float64 csIresData_dTheta;                         /* 由红外测量计算的俯仰角速度 */

    /* 输出变量 */
    float64 csAttCoreData_Rate_c[3];                   /* 滚动/俯仰/偏航姿态角速度控制误差 */
    float64 csAttCoreData_w_Clp[3];                    /* 星体惯性角速度(闭环) [ωx_Clp,ωy_Clp,ωz_Clp] */
    float64 csAttCoreData_q_ESG[4];                    /* 惯性姿态四元数(红外) */
    float64 csAttCoreData_Cbo_Clp[3][3];               /* 定姿引入闭环的方向余弦阵（从轨道坐标系到本体坐标系） */

    /* 输入输出变量 */
    float64 csAttCoreData_A_Clp[3];                    /* 星体三轴姿态(闭环) */
    float64 csAttCoreData_Rate_Clp[3];                 /* 星体三轴姿态角速度(闭环) */
    float64 csAttCoreData_wbo_Clp[3];                  /* 星体相对轨道系的惯性角速度(闭环) */
    float64 csAttCoreData_q_STG[4];                    /* 惯性姿态四元数(星敏)     */
    float64 csAttCoreData_A_c[3];                      /* 滚动/俯仰/偏航姿态角控制误差 */
    float64 csAttCoreData_w_STG[3];                    /* 星体惯性角速度(星敏陀螺) [ωx_STG, ωy_STG, ωz_STG] */
    float64 csAttCoreData_A_ESG[3];                    /* 星体三轴姿态(红外+陀螺) */
    float64 csAttCoreData_Cbo_ESG[3][3];               /* 红外陀螺估计的方向余弦阵(从轨道坐标系到本体坐标系) */
    float64 csAttCoreData_qbt[4];

    /* 状态变量*/
    float64 csAttCoreData_angqbt_Lst;                  /* qBt反算的欧拉角 */
    float64 csAttCoreData_wbo_Lst[20][3];              /* 星体ωbo的历史值 */
    float64 csAttCoreData_A_c_Lst[3];                  /* 滚动/俯仰/偏航角度控制误差历史值 */

    /* 参数变量 */
    unint32 csAntPara_LmtH_Num_dw;                     /* 运动补偿加速度平滑周期数最大值 */

} CS_Ctrl_Att_Rate;

#endif // __CS_CTRL_ATT_RATE_H__
#include "NWM.h"
#include "CS_AttCtrl_Propel.h"

void PhasePlaneJetControl(void *p , float64 ThetaC_in, float64 dThetaC_in, unint32 axis, float64 as_PP, float64 aL_PP, unint32 mode);
void CS_Chose_Switching_Line(void *p, unint32 mode);
void CS_AttCtrl_JetPulseCalc(void *p);
unint32 CS_ThrParamCfgX(unint32 m_WorkMode, float64 *ModeObjectTimer_Mode ,float64 csModePara_dt_PanelUnfold_Start ,
                        unint32 csSGAttAcqData_F_EarthAcq, unint32 csSGAttAcqData_F_YawCapt,
                        unint32 csIomScanPara_FP_GK_JetBack, unint32 csIomScanData_SMODE,
                        unint32 *csCtrlerOtherPara_FP_RWorCMGC, unint32 csWacqData_m_SubMode,
                        unint32 csJPCData_F_UldT);
void CS_AttCtrl_JetCrossSub(unint32 i, unint32 j, float64* csJPCData_mPhase_T, unint32* csJPCData_F_Jet, unint32* csJPCData_FJ);
void CS_AttCtrl_JetCrossCtrl(void *p);
void CS_FindMinMaxPos(unint32 *MinPos, unint32 *MaxPos, const float64 *a, const unint32 length);
void CS_AttCtrl_Jet12Dis(void *p);

void CS_AttCtrl_PropelFun(void *p)
{
    CS_AttCtrl_Propel *pIp = (CS_AttCtrl_Propel*)p;
    unint32 i;

    /* apn 赋值，给推力器故障诊断用 */
    for(i=0; i<3; i++)
    {
    	apn[i][0] = as[ID_Mass][FU_thrGr&0x3][2*i+ 0] * DEG2RAD;
    	apn[i][1] = as[ID_Mass][FU_thrGr&0x3][2*i+ 1] * DEG2RAD;
    }

    /* 调用5.6.3.1.1（姿态三轴期望脉宽计算） */
    CS_AttCtrl_JetPulseCalc(pIp);

    /* 调用5.6.3.1.2(姿控三轴脉宽交叉控) */
    CS_AttCtrl_JetCrossCtrl(pIp);

    /* 停控 或 无推力器可用 */
    if ((F_StopCtrl == 1) || (FU_thrGr == 0))
    {
        ThrGr[0] = 0.0;
        ThrGr[1] = 0.0;
        ThrGr[2] = 0.0;
    }
    else
    {
        CS_AttCtrl_Jet12Dis(pIp);

        /* 计算各喷管的输出脉宽 */
        for (i=0; i<12; i++)
        {
            ThrGr[i] = pIp->csJPCData_t_AC[i];

        }
    }

    return;

}

unint32 CS_ThrParamCfgX(unint32 m_WorkMode, float64 *ModeObjectTimer_Mode ,float64 csModePara_dt_PanelUnfold_Start ,
                        unint32 csSGAttAcqData_F_EarthAcq, unint32 csSGAttAcqData_F_YawCapt,
                        unint32 csIomScanPara_FP_GK_JetBack, unint32 csIomScanData_SMODE,
                        unint32 *csCtrlerOtherPara_FP_RWorCMGC, unint32 csWacqData_m_SubMode,
                        unint32 csJPCData_F_UldT) {
    unint32 mode;

    /* 按条件确定选第几种工况的相平面系数 */
    // WKMD_EIM 0x01u WKMD_AAM 0x08u
    // WKMD_OAM 0x06u WKMD_IOM 0x0Cu
    // WKMD_OCM 0x07u SUBMD_AAM_SPSM 0x02u
    if ((m_WorkMode == 0x01u) && (ModeObjectTimer_Mode[m_WorkMode] < csModePara_dt_PanelUnfold_Start))
    {
        mode = 0;              /* 工况1参数 */
    }
    else if((m_WorkMode == 0x06u) ||
            (m_WorkMode == 0x07u) ||
            ((m_WorkMode == 0x08u) && (csSGAttAcqData_F_EarthAcq == 1)) ||
            ((m_WorkMode == 0x08u) && (csSGAttAcqData_F_EarthAcq == 0) && (csSGAttAcqData_F_YawCapt == 1)) ||
            ((m_WorkMode == 0x0Cu) && (csIomScanPara_FP_GK_JetBack == 1) && (csIomScanData_SMODE == 10))  )

    {
        mode = 1;              /* 工况2参数 */
    }
    else
    {
        if ((m_WorkMode == 0x08u) &&
            (csCtrlerOtherPara_FP_RWorCMGC[0x08u] == 0) &&
            (csWacqData_m_SubMode == 0x02u))
        {
            /* 喷气对日 */
            mode = 2;          /* 工况3参数 */
        }
        else if (csJPCData_F_UldT == 1)
        {
            mode = 3;          /* 工况4参数 */
        }
        else
        {
            mode = 4;          /* 工况5参数 */
        }
    }

    return mode;
}

void CS_AttCtrl_JetPulseCalc(void *p)
{
    CS_AttCtrl_Propel *pIp = (CS_AttCtrl_Propel*)p;
    unint32 mode;


    /* 输入变量 */
    // ipCS_Chose_Switching_Line.mode = mode;
    /* (1) 确定选第几种工况的相平面系数 */
    mode = CS_ThrParamCfgX(WorkMode, &Timer_Mode[0], dt_PanelUnfold_Start,
                            F_EarthAcq, F_YawCapt,
                            FP_GK_JetBack, SMODE,
                            &FP_RWorCMGC[0], m_SubMode,
                            F_UldT );

    /* (2) */
    CS_Chose_Switching_Line(pIp, mode);
    return;
}


void CS_Chose_Switching_Line(void *p, unint32 mode)
{
    CS_AttCtrl_Propel *pIp = (CS_AttCtrl_Propel*)p;
    float64 dA0[3];         /* 姿态机动起始姿态角速度 */
    float64 ThetaC_in;
    float64 dThetaC_in;
    float64 as_PP;          /* 小推力加速度,deg/s^2 */
    float64 aL_PP;          /* 大推力加速度,deg/s^2 */
    unint32 axis;           /* 三轴通道 */

    for (axis=0; axis<3; axis++)        /* axis = 0/1/2对应滚动、俯仰、偏航通道 */
    {
        ThetaC_in = Atti_C[axis] * RAD2DEG;

        if (Fabsx(ThetaC_in) > theta_bp[mode][axis])
        {
            dA0[axis] = -w_bp[mode][axis] * (float64)Sgn2(ThetaC_in);  /* 符号  */
        }
        else
        {
            dA0[axis] = 0.0;
        }

        dThetaC_in = dAtti_C[axis] * RAD2DEG - dA0[axis];

        if (Atti_C[axis] > 0)
        {
            /* as_neg */
            as_PP = as[ID_Mass][FU_thrGr&0x3][2*axis+1];
        }
        else
        {
            /* as_pos */
            as_PP = as[ID_Mass][FU_thrGr&0x3][2*axis+0];
        }

        as_PP = as_PP * Mdf_as_PP;

        /* 默认aL_PP等于as_PP，若型号有特殊要求需单独处理 */
        aL_PP = as_PP;

        /* 调用《直线型相平面喷气姿态控制算法产品规范》 */
        PhasePlaneJetControl(pIp, ThetaC_in, dThetaC_in, axis , as_PP , aL_PP, mode);
        
        if (mPhase_Region[axis] == 0x13)
        {
            ThrGr[axis] = LimitDouble(ThrGr[axis], Mlf_t_R13);
        }

        if (ThrGr[axis] > 0.0)
        {
            F_st[axis] = 1;
        }
        else
        {
            F_st[axis] = 0;
            ThrGr[axis] = -ThrGr[axis];
        }

        F_Jet[axis] = mPhase_FJB[axis];
    }

    return;
}

void PhasePlaneJetControl(void *p , float64 ThetaC_in, float64 dThetaC_in, unint32 axis, float64 as_PP, float64 aL_PP, unint32 mode)
{
    CS_AttCtrl_Propel *pIp = (CS_AttCtrl_Propel*)p;
    siint32 SgnA;
    float64 ThetaC;
    float64 dThetaC;
    float64 Switch1;
    float64 Switch2;
    float64 Switch3;
    float64 tmp_pst;
    float64 TN1;
    float64 TN2;
    float64 tmp_TN;

    SgnA = Sgn2(ThetaC_in);
    ThetaC = SgnA * ThetaC_in;
    dThetaC = SgnA * dThetaC_in;
    tmp_pst = ThetaC + pIp->csJPCPara_Param_PP[mode][axis].ThetaV;

    /* 开关线为直线 */
    Switch1 = ThetaC - pIp->csJPCPara_Param_PP[mode][axis].ThetaD + pIp->csJPCPara_Param_PP[mode][axis].Kj1 * dThetaC;
    Switch2 = ThetaC + pIp->csJPCPara_Param_PP[mode][axis].ThetaD + pIp->csJPCPara_Param_PP[mode][axis].Kj1 * dThetaC;
    Switch3 = ThetaC - pIp->csJPCPara_Param_PP[mode][axis].ThetaB + pIp->csJPCPara_Param_PP[mode][axis].Kj2 * dThetaC;

    /* 初始为0区 */
    mPhase_Region[axis] = 0;

    /* 相区判断 */
    if(Switch1 >= 0.0)
    {
        /* 开关线1的右边：R11、R12、R13 区 */
        if(dThetaC >= pIp->csJPCPara_Param_PP[mode][axis].dThetaS)
        {
            /* R11区 */
            mPhase_Region[axis] = 0x11;
            mPhase_FJB[axis] = 0xA;  /* 大喷 */
            ThrGr[axis] = pIp->csJPCPara_Param_PP[mode][axis].Tmax;
            mPhase_ThetaC_pst[axis]= tmp_pst;
        }
        else
        {
            /* R12 R13区 */
            if(Switch3 < 0.0)
            {
                if((dThetaC < pIp->csJPCPara_Param_PP[mode][axis].dThetaV) && (dThetaC >= 0.0))
                {
                    /* R13区 */
                    mPhase_Region[axis] = 0x13;

                    if(ThetaC < mPhase_ThetaC_pst[axis])
                    {
                        mPhase_FJB[axis] = 0x0;/* 不喷 */
                        ThrGr[axis] = 0.0;
                        if(tmp_pst < mPhase_ThetaC_pst[axis])
                        {
                            /* 即：(Thetac-Thetac_pst+ ThetaV)<0 */
                            mPhase_ThetaC_pst[axis] = tmp_pst;
                        }
                    }
                    else
                    {
                        mPhase_FJB[axis] = 0x5;  /* 小喷 */
                        mPhase_ThetaC_pst[axis] = tmp_pst;

                        TN1 = dThetaC / as_PP;
                        TN2 = pIp->csJPCPara_Param_PP[mode][axis].KJ * (ThetaC - pIp->csJPCPara_Param_PP[mode][axis].Dtheta) / as_PP;
                        tmp_TN = 0.5 * pIp->csJPCPara_Param_PP[mode][axis].Tmax;

                        if(TN2 >= tmp_TN)
                        {
                            TN2 = tmp_TN;
                        }

                        ThrGr[axis] = TN1 + TN2;

                        if(ThrGr[axis] < pIp->csJPCPara_Param_PP[mode][axis].Tmin)
                        {
                            ThrGr[axis] = pIp->csJPCPara_Param_PP[mode][axis].Tmin;
                        }
                    }
                }
                /* else */
                if(dThetaC >= pIp->csJPCPara_Param_PP[mode][axis].dThetaV)
                {
                    /* R12区 */
                    mPhase_Region[axis] = 0x12;
                    mPhase_FJB[axis] = 0x5;  /* 小喷 */
                    ThrGr[axis] = pIp->csJPCPara_Param_PP[mode][axis].Tmax;
                    mPhase_ThetaC_pst[axis] = tmp_pst;
                }
            }
        }
    }

    if((Switch2 < 0.0) && (dThetaC < 0.0))  /* R21区 */
    {
        mPhase_Region[axis]=0x21;
        mPhase_FJB[axis] = 0xA; /* 大喷 */
        ThrGr[axis] = -pIp->csJPCPara_Param_PP[mode][axis].Tmax;
        mPhase_ThetaC_pst[axis] = tmp_pst;
    }
    if (Switch3 >= 0.0)
    {
        /* R15 R16 R17区 */
        if(dThetaC < -pIp->csJPCPara_Param_PP[mode][axis].dThetaLL)
        {
            /* R17区 */
            mPhase_Region[axis]=0x17;
            mPhase_FJB[axis] = 0xA; /* 大喷 */
            ThrGr[axis] =  -pIp->csJPCPara_Param_PP[mode][axis].Tmax;
            mPhase_ThetaC_pst[axis] = tmp_pst;
        }
        else
        {
            /* R15 R16区 */
            if((dThetaC >= 0.0) && (dThetaC < pIp->csJPCPara_Param_PP[mode][axis].dThetaS))
            {
                /* R15区 */
                mPhase_Region[axis]=0x15;
                mPhase_FJB[axis] = 0xA; /* 大喷 */
                ThrGr[axis]= (dThetaC + pIp->csJPCPara_Param_PP[mode][axis].dThetaL)/ aL_PP + pIp->csJPCPara_Param_PP[mode][axis].Tmin;
                mPhase_ThetaC_pst[axis] = tmp_pst;
            }
            if((dThetaC < 0.0) && (dThetaC >= -pIp->csJPCPara_Param_PP[mode][axis].dThetaL))
            {
                /* R16区 */
                mPhase_Region[axis]=0x16;
                mPhase_FJB[axis] = 0xA; /* 大喷 */
                ThrGr[axis]=(pIp->csJPCPara_Param_PP[mode][axis].dThetaL + dThetaC)/ aL_PP + pIp->csJPCPara_Param_PP[mode][axis].Tmin;
                mPhase_ThetaC_pst[axis] = tmp_pst;
            }

        }
    }
    else
    {
        /* R14区 */
        if ((dThetaC < 0.0) && (dThetaC >= -pIp->csJPCPara_Param_PP[mode][axis].dThetaL) && (ThetaC >= pIp->csJPCPara_Param_PP[mode][axis].ThetaD))
        {
            mPhase_Region[axis]=0x14;
            if (ThetaC >= mPhase_ThetaC_pst[axis])
            {
                mPhase_FJB[axis] = 0x5;  /* 小喷 */
                ThrGr[axis] = pIp->csJPCPara_Param_PP[mode][axis].Tmin;
                mPhase_ThetaC_pst[axis] = tmp_pst;
            }
            else
            {
                mPhase_FJB[axis] = 0x0;  /* 不喷 */
                ThrGr[axis] = 0.0;
                if(tmp_pst < mPhase_ThetaC_pst[axis])
                {
                    /* 即：(Thetac-Thetac_pst+ ThetaV)<0 */
                    mPhase_ThetaC_pst[axis] = tmp_pst;
                }
            }
        }
    }

    if(mPhase_Region[axis] == 0x0)
    {
        /* R0区 */
        mPhase_FJB[axis] = 0x0;
        ThrGr[axis] = 0.0;
        mPhase_ThetaC_pst[axis] = ThetaC - pIp->csJPCPara_Param_PP[mode][axis].ThetaV;
    }

    /* 喷气脉宽限幅 */
    ThrGr[axis] = LimitDouble(ThrGr[axis], pIp->csJPCPara_Param_PP[mode][axis].Tmax);

    if (SgnA > 0)
    {
        ThrGr[axis] = -ThrGr[axis];
    }

    return;
}


void CS_AttCtrl_JetCrossSub(unint32 i, unint32 j, float64* csJPCData_mPhase_T, unint32* csJPCData_F_Jet, unint32* csJPCData_FJ)
{
    if ((csJPCData_mPhase_T[i] * csJPCData_mPhase_T[j]) > 1.0e-5)
    {
        if ((csJPCData_F_Jet[i] < csJPCData_F_Jet[j]) ||
            ((csJPCData_FJ[i + j - 1] == 0) && (csJPCData_F_Jet[i] == csJPCData_F_Jet[j])))
        {
            csJPCData_F_Jet[i] = 0;
            csJPCData_mPhase_T[i] = 0;
            csJPCData_FJ[i + j - 1] = 0x1; /* 本次控j轴 */
        }
        if (csJPCData_mPhase_T[i] > 1.0e-5)
        {
            csJPCData_F_Jet[j] = 0;
            csJPCData_mPhase_T[j] = 0;
            csJPCData_FJ[i + j - 1] = 0x0; /* 本次控i轴 */
        }

    }

    return;
}

void CS_AttCtrl_JetCrossCtrl(void *p)
{
    CS_AttCtrl_Propel *pIp = (CS_AttCtrl_Propel*)p;

    /* XY轴姿控耦合交叉控制 */
    if (pIp->csJPCPara_FP_FJXYZ == 0x1)
    {
        CS_AttCtrl_JetCrossSub(0,1,ThrGr,F_Jet,FJ);
    }

    /* XZ轴姿控耦合交叉控制 */
    else if (pIp->csJPCPara_FP_FJXYZ == 0x2)
    {
        CS_AttCtrl_JetCrossSub(0,2,ThrGr,F_Jet,FJ);
    }
    else
    {
        /* YZ轴姿控耦合交叉控制 */
        if (pIp->csJPCPara_FP_FJXYZ == 0x3)
        {
            CS_AttCtrl_JetCrossSub(1,2,ThrGr,F_Jet,FJ);
        }
    }


    //return;
}



void CS_FindMinMaxPos(unint32 *MinPos, unint32 *MaxPos, const float64 *a, const unint32 length)
{
    unint32 i;
    float64 min = 0.0;
    float64 max = 0.0;

    for (i=0; i<length; i++)
    {
        if (a[i] != 0.0)
        { /* 找第一个非0值作为最大值和最小值的初值，并记下其序号 */
            min = a[i];
            max = a[i];
            *MinPos = i;
            *MaxPos = i;
            break;
        }
    }

    for (; i<length; i++)   /* i接着上面循环的值 */
    {
        if (a[i] != 0.0)
        {
            if (a[i] < min)
            {
                min     = a[i];
                *MinPos = i;
            }
            if (a[i] >= max)
            {
                max     = a[i];
                *MaxPos = i;
            }
        }
    }
    return;
}

void CS_AttCtrl_Jet12Dis(void *p)
{
    CS_AttCtrl_Propel *pIp = (CS_AttCtrl_Propel*)p;
    float64 t_Thr_tmp[12][6];
    float64 sum_T, dt_Thr;
    float64 asTmp;
    unint32 k_max = 0;
    unint32 k_min = 0;
    unint32 k_mod;
    unint32 i, j, axis;
    unint32 sum_N, sum_N2;

    sum_N2 = 0;

    Memsetx((unint08 *)&t_Thr_tmp[0][0], 0x0, sizeof(t_Thr_tmp));

    /* (1) 推力器分配 */
    /* a.1 */
    for (i=0; i<12; i++)
    {/* 所有姿控喷管 */

        pIp->csJPCData_t_AC[i] = 0.0;
        for (j=0; j<3; j++)
        {
            if (F_st[j] == 1)
            {
                t_Thr_tmp[i][2*j] = ThrGr[j] * (float64)(F_Assign[FU_thrGr&0x3][i][2*j]);
            }
            else
            {
                t_Thr_tmp[i][2*j+1] = ThrGr[j] * (float64)(F_Assign[FU_thrGr&0x3][i][2*j+1]);
            }
        }
    }

    /* a.2 对每个喷管，依次进行判断 */
    for (i=0; i<12; i++)
    {
        sum_T  = 0.0;           /* 清零 */
        sum_N  = 0;

        for (j=0; j<6; j++)
        {
            sum_N = sum_N + F_Assign[FU_thrGr&0x3][i][j];
            sum_T = sum_T + t_Thr_tmp[i][j];
        }
        dt_Thr = sum_T - Tc;

        if ((sum_N == 2) && (dt_Thr > 0.0))
        {
            CS_FindMinMaxPos( &k_min, &k_max,t_Thr_tmp[i], 6);

            if (k_min == F_AssignUse[i])
            {
                k_mod = k_max;
            }
            else
            {
                k_mod = k_min;
            }

            F_AssignUse[i] = k_mod;

            for (j=0; j<12; j++)
            {
                t_Thr_tmp[j][k_mod] = Maxx((t_Thr_tmp[j][k_mod] - dt_Thr), 0.0);
            }

            for (j=0; j<3; j++)
            {
                if ((k_mod == (2 * j)) || (k_mod == ( (2 * j) + 1)))
                {
                    ThrGr[j] = Maxx((ThrGr[j] - dt_Thr), 0.0);
                    break;
                }
            }
        }

    }

    for (i=0; i<12; i++)
    {
        /* 计算各喷管的输出脉宽 */
        for (j=0; j<6; j++)
        {
            pIp->csJPCData_t_AC[i] = pIp->csJPCData_t_AC[i] + t_Thr_tmp[i][j];
        }

        pIp->csJPCData_t_AC[i] = LimitDouble(pIp->csJPCData_t_AC[i], Tc);
    }

    /* b. 加速度计算及喷气时间累计 */
    for (axis=0; axis<3; axis++)
    {
        if (F_st[axis] == 1)
        {
            sum_N2 = 0;

            /* 从as配置数组中取出a_p */
            asTmp = as[ID_Mass][FU_thrGr&0x3][2*axis + 0] * DEG2RAD;

            a[axis] = ThrGr[axis] / Tc * asTmp * Mdf_as_ACReal;

            for (i = 0; i < 12; i++)
            {
                /* 2*axis  F_Assign[轴1正 轴1负 轴二正 轴二负 轴三正 轴三负] */
                sum_N2 = sum_N2 + F_Assign[FU_thrGr&0x3][i][2 * axis];
            }
            SumTp[axis] = SumTp[axis] + (float64)(sum_N2) * ThrGr[axis];
        }
        else
        {
            sum_N2 = 0;

            /* 从as配置数组中取出a_n */
            asTmp = as[ID_Mass][FU_thrGr&0x3][2*axis + 1] * DEG2RAD;

            a[axis] = -ThrGr[axis] / Tc * asTmp * Mdf_as_ACReal;

            for (i=0; i<12; i++)
            {
                /* 2*axis  F_Assign[轴1正 轴1负 轴二正 轴二负 轴三正 轴三负] */
                sum_N2 = sum_N2 + F_Assign[FU_thrGr&0x3][i][2 * axis + 1];
            }
            SumTn[axis] = SumTn[axis] + (float64)(sum_N2) * ThrGr[axis];
        }
    }

    /* 5.6.3.1.7    推力器三轴喷气累计及加速度计算 */
    // CS_AttCtrl_SumCalc();
    float64 tmpSumTorq;

    /* 姿控推力器加速度和三轴累计脉宽计算 */
    for (i=0; i<3; i++)
    {
        tmpSumTorq = 0.0;

        for (j=0; j<12; j++)   //NUM_THRGR
        {
            tmpSumTorq += Torq[j][i] * pIp->csJPCData_t_AC[j];
        }

        /* 计算角加速度 */
        a2[i] = tmpSumTorq * Mdf_as_ACReal / Tc / Js_All[i][i];

        /* 喷气时间累计 */
        if (a2[i] > 0.0)
        {
            SumTp2[i] += a2[i] / (apn[i][0] * Mdf_as_ACReal) * Tc;
        }
        else
        {
            SumTn2[i] += Fabsx(a2[i]) / (apn[i][1] * Mdf_as_ACReal) * Tc;
        }
    }

    return;
}
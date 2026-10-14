#include "CS_IRES_Attitude.h"

void CS_IRES_Modify(void *p);
void IRES_DataProcess( void *p);
void StaticIresConvert(void *p);
void CS_IRES_ValidCheck_Convert( void *p );

void CS_IRES_AttitudeFun(void *p)
{
    CS_IRES_Attitude *pIp = (CS_IRES_Attitude*)p;

    unint32 i;
    unint32 j;
    unint32 sum = 0;

    for( j = 0 ; j < 2 ; j++)
    {
        sum = sum + pIp->csIresPara_FS[j];
    }

    /**** start of 规范化算法《红外敏感器有效性判断及数据处理》产品规范 ****/
    if (sum != 0)
    {
        if ( pIp->m_WorkMode == 0x01u )
        {
            /* 红外地球敏感器数据有效性判断和数据处理 */
            CS_IRES_ValidCheck_Convert(pIp);
            
            if ( pIp->ModeObjectTimer_Mode[pIp->m_WorkMode] > pIp->csModePara_dt_ESUsed_EIM )
            {
                /* 5.2.2.2 基于红外滤波的姿态修正 */
                CS_IRES_Modify(pIp);
                
            }
            else
            {
                for (i=0; i<2; i++ )
                {
                    pIp->csIresDiagData_phi_i_Lst[i] = pIp->csIresDiagData_phi_i[i];
                    pIp->csIresDiagData_theta_i_Lst[i] = pIp->csIresDiagData_theta_i[i];
                }
            }
        }
        else if ((pIp->m_WorkMode == 0x02u) ||
                ((pIp->m_WorkMode == 0x05u) && (pIp->csIresCorrPara_FP_IRESUse_AHM == 1)) ||
                ((pIp->m_WorkMode == 0x03u) && (pIp->csPointSunPara_gfhSPAttCalcMode == 2)))
        {
            /* 红外地球敏感器数据有效性判断和数据处理 */
            CS_IRES_ValidCheck_Convert(pIp);
            
            if (( pIp->csAttPara_FS_AttD != 3 ) && ( pIp->csAttPara_FS_AttD != 4 ))
            {
                /* 5.2.2.2 基于红外滤波的姿态修正 */
                CS_IRES_Modify(pIp);
            }
        }
        else
        {
            /* 红外地球敏感器数据有效性判断和数据处理 */
            CS_IRES_ValidCheck_Convert(pIp);
        }
    }
    else
    {
        /* 置红外无效 */
        for (i=0; i<2; i++)
        {
            pIp->csIresDiagData_FV[i] = 0u;
            pIp->csIresDiagData_FU[i] = 0u;
        }
    }
    /**** end of 规范化算法《红外敏感器有效性判断及数据处理》产品规范 ****/

    return;
}


void CS_IRES_ValidCheck_Convert( void *p )
{
    CS_IRES_Attitude *pIp = (CS_IRES_Attitude*)p;
    unint32 i;
    float64 t_phi;
    float64 t_theta;

    if((pIp->csModeData_CycleNum % ((unint32)(pIp->csIresPara_Ts / pIp->m_DeltaT))) == 2)
    {
    	/* 每ESGr.Ts秒，仅考虑型号最多配置两个红外的情况 */
        /* 根据红外地球敏感器类型，调用相应的数据有效性判断程序 */
        MatrixTran(pIp->csIresData_Cbs[0][0], pIp->csIresPara_CbsT[0][0], 3, 3 );

    	/* 静态红外地球敏感器数据处理 */
        StaticIresConvert(pIp);
        
        /* 红外输出的数据处理 */
        IRES_DataProcess(pIp);
        
    }

    /**** end of 规范化算法《红外敏感器有效性判断及数据处理》产品规范 ****/

    return;
}

void StaticIresConvert(void *p)
{
    CS_IRES_Attitude *pIp = (CS_IRES_Attitude*)p;
    /* (1) */
    if (pIp->csIresData_FHV[0] == 1)
    {
        pIp->csIresDiagData_Em[0][2] = pIp->csIresData_S_Emz[0] * Sqrtx( Fabsx(1.0 - pIp->csIresDiagData_Em[0][0] * pIp->csIresDiagData_Em[0][0] - pIp->csIresDiagData_Em[0][1] * pIp->csIresDiagData_Em[0][1] ) );

        MatrixMulti331(pIp->csIresDiagData_Eb_i[0], &pIp->csIresData_Cbs[0][0][0], pIp->csIresDiagData_Em[0]);

        pIp->csIresDiagData_phi_i[0] = Atan2x( pIp->csIresDiagData_Eb_i[0][1], pIp->csIresDiagData_Eb_i[0][2] ) + pIp->csIresPara_dphib_Comps[0];
        pIp->csIresDiagData_theta_i[0] = - Asinx( pIp->csIresDiagData_Eb_i[0][0] ) + pIp->csIresPara_dthetab_Comps[0];
    }

    /* (2)根据红外单机状态标志进行有效性判断 */
    pIp->csIresDiagData_FV[0] = pIp->csIresData_FHV[0];

    if ( pIp->csIresPara_FS[0] == 0 )
    {
        pIp->csIresDiagData_FV[0] = 0;
    }

    /* (3)进行红外数据常值故障的有效性判断 */
    if ((pIp->csIresDiagPara_FP_ESProc[pIp->m_WorkMode] == 1) && (pIp->csIresDiagData_FV[0] == 1))
    {
        if (Fabsx(pIp->csIresDiagData_Em[0][0] - pIp->csIresDiagData_Em_Lst[0][0]) < pIp->csIresDiagPara_LmtEm_ConstErr)
        {
            pIp->csIresDiagData_CntEmx_ConstErr[0]++;
        }
        else
        {
            pIp->csIresDiagData_CntEmx_ConstErr[0] = 0;
        }

        if (Fabsx(pIp->csIresDiagData_Em[0][1] - pIp->csIresDiagData_Em_Lst[0][1]) < pIp->csIresDiagPara_LmtEm_ConstErr)
        {
            pIp->csIresDiagData_CntEmy_ConstErr[0]++;
        }
        else
        {
            pIp->csIresDiagData_CntEmy_ConstErr[0] = 0;
        }

        if ((pIp->csIresDiagData_CntEmx_ConstErr[0] >= pIp->csIresDiagPara_LmtN_ConstErr)
            || (pIp->csIresDiagData_CntEmy_ConstErr[0] >= pIp->csIresDiagPara_LmtN_ConstErr))
        {
            pIp->csIresDiagData_FV[0] = 0;
        }
    }
    else
    {
    	pIp->csIresDiagData_CntEmx_ConstErr[0] = 0;
        pIp->csIresDiagData_CntEmy_ConstErr[0] = 0;
    }	

    /* (4) 历史值赋值 */
    pIp->csIresDiagData_Em_Lst[0][0] = pIp->csIresDiagData_Em[0][0];
    pIp->csIresDiagData_Em_Lst[0][1] = pIp->csIresDiagData_Em[0][1];

    return;
}

void IRES_DataProcess( void *p)
{
    CS_IRES_Attitude *pIp = (CS_IRES_Attitude*)p;
    unint32 i;
    unint32 cntValid;
    unint32 idxValid[2];

    /* 有效红外个数初值置零 */
    cntValid = 0;

    /* 按顺序挑选出有效红外，将其索引号暂存于idxValid中，最多挑两个 */
    for (i = 0; i < 2; i++)
    {
        if (pIp->csIresDiagData_FV[i] == 1)  /* 该红外有效 */
        {
            idxValid[cntValid] = i;

            cntValid++;
        }

        if (cntValid >= 2)  /* 最多挑两个 */
        {
            break;
        }
    }

    /* (1) */
    pIp->csIresData_phi_Lst2 = pIp->csIresData_phi_Lst;
    pIp->csIresData_phi_Lst = pIp->csIresData_phi;

    pIp->csIresData_theta_Lst2 = pIp->csIresData_theta_Lst;
    pIp->csIresData_theta_Lst = pIp->csIresData_theta;

    /* (2) */
    if (cntValid >= 2)  /* 有效红外个数为两个或以上 */
    {
        /* 选用前两个有效红外数据 */
        pIp->csIresData_phi   = 0.5 * (pIp->csIresDiagData_phi_i[idxValid[0]] + pIp->csIresDiagData_phi_i[idxValid[1]]);
        pIp->csIresData_theta = 0.5 * (pIp->csIresDiagData_theta_i[idxValid[0]] + pIp->csIresDiagData_theta_i[idxValid[1]]);
    }
    else
    {
        if (cntValid == 1)  /* 只有一个红外有效 */
        {
            pIp->csIresData_phi = pIp->csIresDiagData_phi_i[idxValid[0]];
            pIp->csIresData_theta = pIp->csIresDiagData_theta_i[idxValid[0]];
        }
    }

    pIp->csIresDiagData_Eb[0] = - Sinx( pIp->csIresData_theta - pIp->csIresPara_dtheta_Comps);
    pIp->csIresDiagData_Eb[1] =   Sinx( pIp->csIresData_phi - pIp->csIresPara_dphi_Comps ) * Cosx( pIp->csIresData_theta - pIp->csIresPara_dtheta_Comps);
    pIp->csIresDiagData_Eb[2] =   Cosx(pIp->csIresData_phi - pIp->csIresPara_dphi_Comps) * Cosx(pIp->csIresData_theta - pIp->csIresPara_dtheta_Comps);

    /* (3) */
    if (cntValid > 0)  /* 至少有一个红外有效 */
    {
        pIp->csIresData_dPhi = pIp->csIresCorrPara_Mdf_f_dphi * pIp->csIresData_dPhi +
                          (1.0 - pIp->csIresCorrPara_Mdf_f_dphi) * (pIp->csIresData_phi - pIp->csIresData_phi_Lst2) /
                            2.0 / pIp->csIresPara_Ts;

        pIp->csIresData_dPhi = LimitDouble(pIp->csIresData_dPhi, pIp->csIresCorrPara_Mlf_dphi);

        pIp->csIresData_dTheta = pIp->csIresCorrPara_Mdf_f_dphi * pIp->csIresData_dTheta +
                            (1.0 - pIp->csIresCorrPara_Mdf_f_dphi) * (pIp->csIresData_theta - pIp->csIresData_theta_Lst2) /
                            2.0 / pIp->csIresPara_Ts;

        pIp->csIresData_dTheta = LimitDouble(pIp->csIresData_dTheta, pIp->csIresCorrPara_Mlf_dtheta);
    }
    else   /* 所有红外都无效 */
    {
        pIp->csIresData_dPhi = 0.0;
        pIp->csIresData_dTheta = 0.0;
    }

    return;
}

void    CS_IRES_Modify(void *p)
{
    CS_IRES_Attitude *pIp = (CS_IRES_Attitude*)p;

    unint32 i;
    float64 t_IresAngle[2], t_DevIresAngle[2];
    float64 cosPsi_ESG;
    float64 tmpK_CorrDeltaPhi_ESG[6];

    IresFilterParam t_FilterParam;
    unint32 j;
    unint32 sum = 0;
    for( j = 0 ; j < 2 ; j++)
    {
        sum = sum + pIp->csIresDiagData_FU[j];
    }

    if ((pIp->csModeData_CycleNum % ((unint32)(pIp->csIresPara_Ts / pIp->m_DeltaT))) == 2)
    {   /* 红外更新周期  */

        if ( sum > 0 )
        {
            /* @调用《基于红外测量的红外滤波修正算法产品规范》 */
            /* extern void IresModify(float64 *Angle, float64 *Gyrob, float64 *Gyrod, const float64 *IresAngle,
            const float64 *DevIresAngle, SIresFilterParam FilterParam); */
            t_IresAngle[0]    = pIp->csIresData_phi;
            t_IresAngle[1]    = pIp->csIresData_theta;
            t_DevIresAngle[0] = pIp->csIresPara_dphi_Comps;
            t_DevIresAngle[1] = pIp->csIresPara_dtheta_Comps;
            t_FilterParam.lmtDevAngle[0] = pIp->csIresCorrPara_Mlf_dphi;
            t_FilterParam.lmtDevAngle[1] = pIp->csIresCorrPara_Mlf_dtheta;
            Memcpyx((unint08 *)t_FilterParam.Kg, (unint08 *)pIp->csIresCorrPara_K_CorrDe_ESG, sizeof(t_FilterParam.Kg));

            cosPsi_ESG = Cosx(pIp->csAttCoreData_A_ESG[2]);
            tmpK_CorrDeltaPhi_ESG[0] = pIp->csIresCorrPara_K_Corrdphi_ESG[0];
            tmpK_CorrDeltaPhi_ESG[1] = pIp->csIresCorrPara_K_Corrdphi_ESG[1] * cosPsi_ESG;
            tmpK_CorrDeltaPhi_ESG[2] = pIp->csIresCorrPara_K_Corrdphi_ESG[2];
            tmpK_CorrDeltaPhi_ESG[3] = pIp->csIresCorrPara_K_Corrdphi_ESG[3] * cosPsi_ESG;
            tmpK_CorrDeltaPhi_ESG[4] = pIp->csIresCorrPara_K_Corrdphi_ESG[4];
            tmpK_CorrDeltaPhi_ESG[5] = pIp->csIresCorrPara_K_Corrdphi_ESG[5] * cosPsi_ESG;
            Memcpyx((unint08 *)t_FilterParam.KH1, (unint08 *)tmpK_CorrDeltaPhi_ESG, sizeof(t_FilterParam.KH1));

            Memcpyx((unint08 *)t_FilterParam.KH2, (unint08 *)pIp->csIresCorrPara_K_Corrdtheta_ESG, sizeof(t_FilterParam.KH2));

            //IPCREATE(IresModify,ipIresModify,.*Angle=pIp->csAttCoreData_A_ESG,.*Gyrob=pIp->csGyroData_D0_ESCorr,.*Gyrod=pIp->csGyroData_De_ESCorr,.*IresAngle=t_IresAngle,.*DevIresAngle=t_DevIresAngle,.FilterParam=t_FilterParam);
            unint32 k;
            float64 devangle[2];

            for(k = 0; k < 2; k++)
            {
                devangle[i] = t_IresAngle[i] - pIp->csAttCoreData_A_ESG[i] - t_DevIresAngle[i];
                devangle[i] = LimitDouble(devangle[i], t_FilterParam.lmtDevAngle[i]);
            }
            /* 姿态角估计值  */
            /* 常漂、随漂估计值  */
            pIp->csAttCoreData_A_ESG[0] = pIp->csAttCoreData_A_ESG[0] + t_FilterParam.KH1[0] * devangle[0];
            pIp->csAttCoreData_A_ESG[2] = pIp->csAttCoreData_A_ESG[2] + t_FilterParam.KH1[1] * devangle[0];
            pIp->csGyroData_De_ESCorr[0] = t_FilterParam.Kg[0] * pIp->csGyroData_De_ESCorr[0] + t_FilterParam.KH1[2] * devangle[0];
            pIp->csGyroData_De_ESCorr[2] = t_FilterParam.Kg[2] * pIp->csGyroData_De_ESCorr[2] + t_FilterParam.KH1[3] * devangle[0];
            pIp->csGyroData_D0_ESCorr[0] = pIp->csGyroData_D0_ESCorr[0] + t_FilterParam.KH1[4] * devangle[0];
            pIp->csGyroData_D0_ESCorr[2] = pIp->csGyroData_D0_ESCorr[2] + t_FilterParam.KH1[5] * devangle[0];

            pIp->csAttCoreData_A_ESG[1] = pIp->csAttCoreData_A_ESG[1] + t_FilterParam.KH2[0] * devangle[1];
            pIp->csGyroData_De_ESCorr[1] = t_FilterParam.Kg[1] * pIp->csGyroData_De_ESCorr[1] + t_FilterParam.KH2[1] * devangle[1];
            pIp->csGyroData_D0_ESCorr[1] = pIp->csGyroData_D0_ESCorr[1] + t_FilterParam.KH2[2] * devangle[1];

            /* 陀螺漂移限幅 */
            for (i=0; i<3; i++)
            {
                pIp->csGyroData_D0_ESCorr[i] = LimitDouble(pIp->csGyroData_D0_ESCorr[i], pIp->csGyroPara_Mlf_D0);
                pIp->csGyroData_De_ESCorr[i] = LimitDouble(pIp->csGyroData_De_ESCorr[i], pIp->csGyroPara_Mlf_De);
            }
        }
    }

    return;
}
#include "NWM.h"
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
        sum = sum + FS[j];
    }

    /**** start of 规范化算法《红外敏感器有效性判断及数据处理》产品规范 ****/
    if (sum != 0)
    {
        if ( WorkMode == 0x01u )
        {
            /* 红外地球敏感器数据有效性判断和数据处理 */
            CS_IRES_ValidCheck_Convert(pIp);
            
            if ( Timer_Mode[WorkMode] > dt_ESUsed_EIM )
            {
                /* 5.2.2.2 基于红外滤波的姿态修正 */
                CS_IRES_Modify(pIp);
                
            }
            else
            {
                for (i=0; i<2; i++ )
                {
                    pIp->csIresDiagData_phi_i_Lst[i] = phi_i[i];
                    pIp->csIresDiagData_theta_i_Lst[i] = theta_i[i];
                }
            }
        }
        else if ((WorkMode == 0x02u) ||
                ((WorkMode == 0x05u) && (pIp->csIresCorrPara_FP_IRESUse_AHM == 1)) ||
                ((WorkMode == 0x03u) && (FS_SCMType == 2)))
        {
            /* 红外地球敏感器数据有效性判断和数据处理 */
            CS_IRES_ValidCheck_Convert(pIp);
            
            if (( FS_AttD != 3 ) && ( FS_AttD != 4 ))
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
            FV_ES[i] = 0u;
            FU_ES[i] = 0u;
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

    if((CycleNum % ((unint32)(Ts / Tc))) == 2)
    {
    	/* 每ESGr.Ts秒，仅考虑型号最多配置两个红外的情况 */
        /* 根据红外地球敏感器类型，调用相应的数据有效性判断程序 */
        MatrixTran(pIp->csIresData_Cbs[0][0], CbsT[0][0], 3, 3 );

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
    if (FHV_ES[0] == 1)
    {
        Em[0][2] = S_Emz[0] * Sqrtx( Fabsx(1.0 - Em[0][0] * Em[0][0] - Em[0][1] * Em[0][1] ) );

        MatrixMulti331(Eb_i[0], &pIp->csIresData_Cbs[0][0][0], Em[0]);

        phi_i[0] = Atan2x( Eb_i[0][1], Eb_i[0][2] ) + dphib_Comps[0];
        theta_i[0] = - Asinx( Eb_i[0][0] ) + dthetab_Comps[0];
    }

    /* (2)根据红外单机状态标志进行有效性判断 */
    FV_ES[0] = FHV_ES[0];

    if ( FS[0] == 0 )
    {
        FV_ES[0] = 0;
    }

    /* (3)进行红外数据常值故障的有效性判断 */
    if ((FP_ESProc[WorkMode] == 1) && (FV_ES[0] == 1))
    {
        if (Fabsx(Em[0][0] - pIp->csIresDiagData_Em_Lst[0][0]) < LmtEm_ConstErr)
        {
            pIp->csIresDiagData_CntEmx_ConstErr[0]++;
        }
        else
        {
            pIp->csIresDiagData_CntEmx_ConstErr[0] = 0;
        }

        if (Fabsx(Em[0][1] - pIp->csIresDiagData_Em_Lst[0][1]) < LmtEm_ConstErr)
        {
            pIp->csIresDiagData_CntEmy_ConstErr[0]++;
        }
        else
        {
            pIp->csIresDiagData_CntEmy_ConstErr[0] = 0;
        }

        if ((pIp->csIresDiagData_CntEmx_ConstErr[0] >= LmtN_ConstErr)
            || (pIp->csIresDiagData_CntEmy_ConstErr[0] >= LmtN_ConstErr))
        {
            FV_ES[0] = 0;
        }
    }
    else
    {
    	pIp->csIresDiagData_CntEmx_ConstErr[0] = 0;
        pIp->csIresDiagData_CntEmy_ConstErr[0] = 0;
    }	

    /* (4) 历史值赋值 */
    pIp->csIresDiagData_Em_Lst[0][0] = Em[0][0];
    pIp->csIresDiagData_Em_Lst[0][1] = Em[0][1];

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
        if (FV_ES[i] == 1)  /* 该红外有效 */
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
    pIp->csIresData_phi_Lst = Phi_ES;

    pIp->csIresData_theta_Lst2 = pIp->csIresData_theta_Lst;
    pIp->csIresData_theta_Lst = theta_ES;

    /* (2) */
    if (cntValid >= 2)  /* 有效红外个数为两个或以上 */
    {
        /* 选用前两个有效红外数据 */
        Phi_ES   = 0.5 * (phi_i[idxValid[0]] + phi_i[idxValid[1]]);
        theta_ES = 0.5 * (theta_i[idxValid[0]] + theta_i[idxValid[1]]);
    }
    else
    {
        if (cntValid == 1)  /* 只有一个红外有效 */
        {
            Phi_ES = phi_i[idxValid[0]];
            theta_ES = theta_i[idxValid[0]];
        }
    }

    pIp->csIresDiagData_Eb[0] = - Sinx( theta_ES - dtheta_Comps);
    pIp->csIresDiagData_Eb[1] =   Sinx( Phi_ES - dphi_Comps ) * Cosx( theta_ES - dtheta_Comps);
    pIp->csIresDiagData_Eb[2] =   Cosx(Phi_ES - dphi_Comps) * Cosx(theta_ES - dtheta_Comps);

    /* (3) */
    if (cntValid > 0)  /* 至少有一个红外有效 */
    {
        dPhi_ES = Mdf_f_dphi * dPhi_ES +
                          (1.0 - Mdf_f_dphi) * (Phi_ES - pIp->csIresData_phi_Lst2) /
                            2.0 / Ts;

        dPhi_ES = LimitDouble(dPhi_ES, Mlf_dphi);

        dtheta_ES = Mdf_f_dphi * dtheta_ES +
                            (1.0 - Mdf_f_dphi) * (theta_ES - pIp->csIresData_theta_Lst2) /
                            2.0 / Ts;

        dtheta_ES = LimitDouble(dtheta_ES, Mlf_dtheta);
    }
    else   /* 所有红外都无效 */
    {
        dPhi_ES = 0.0;
        dtheta_ES = 0.0;
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
        sum = sum + FU_ES[j];
    }

    if ((CycleNum % ((unint32)(Ts / Tc))) == 2)
    {   /* 红外更新周期  */

        if ( sum > 0 )
        {
            /* @调用《基于红外测量的红外滤波修正算法产品规范》 */
            /* extern void IresModify(float64 *Angle, float64 *Gyrob, float64 *Gyrod, const float64 *IresAngle,
            const float64 *DevIresAngle, SIresFilterParam FilterParam); */
            t_IresAngle[0]    = Phi_ES;
            t_IresAngle[1]    = theta_ES;
            t_DevIresAngle[0] = dphi_Comps;
            t_DevIresAngle[1] = dtheta_Comps;
            t_FilterParam.lmtDevAngle[0] = Mlf_dphi;
            t_FilterParam.lmtDevAngle[1] = Mlf_dtheta;
            Memcpyx((unint08 *)t_FilterParam.Kg, (unint08 *)K_CorrDe_ESG, sizeof(t_FilterParam.Kg));

            cosPsi_ESG = Cosx(Atti_ESG[2]);
            tmpK_CorrDeltaPhi_ESG[0] = K_Corrdphi_ESG[0];
            tmpK_CorrDeltaPhi_ESG[1] = K_Corrdphi_ESG[1] * cosPsi_ESG;
            tmpK_CorrDeltaPhi_ESG[2] = K_Corrdphi_ESG[2];
            tmpK_CorrDeltaPhi_ESG[3] = K_Corrdphi_ESG[3] * cosPsi_ESG;
            tmpK_CorrDeltaPhi_ESG[4] = K_Corrdphi_ESG[4];
            tmpK_CorrDeltaPhi_ESG[5] = K_Corrdphi_ESG[5] * cosPsi_ESG;
            Memcpyx((unint08 *)t_FilterParam.KH1, (unint08 *)tmpK_CorrDeltaPhi_ESG, sizeof(t_FilterParam.KH1));

            Memcpyx((unint08 *)t_FilterParam.KH2, (unint08 *)K_Corrdtheta_ESG, sizeof(t_FilterParam.KH2));

            //IPCREATE(IresModify,ipIresModify,.*Angle=Atti_ESG,.*Gyrob=D0_ESCorr,.*Gyrod=pIp->csGyroData_De_ESCorr,.*IresAngle=t_IresAngle,.*DevIresAngle=t_DevIresAngle,.FilterParam=t_FilterParam);
            unint32 k;
            float64 devangle[2];

            for(k = 0; k < 2; k++)
            {
                devangle[i] = t_IresAngle[i] - Atti_ESG[i] - t_DevIresAngle[i];
                devangle[i] = LimitDouble(devangle[i], t_FilterParam.lmtDevAngle[i]);
            }
            /* 姿态角估计值  */
            /* 常漂、随漂估计值  */
            Atti_ESG[0] = Atti_ESG[0] + t_FilterParam.KH1[0] * devangle[0];
            Atti_ESG[2] = Atti_ESG[2] + t_FilterParam.KH1[1] * devangle[0];
            pIp->csGyroData_De_ESCorr[0] = t_FilterParam.Kg[0] * pIp->csGyroData_De_ESCorr[0] + t_FilterParam.KH1[2] * devangle[0];
            pIp->csGyroData_De_ESCorr[2] = t_FilterParam.Kg[2] * pIp->csGyroData_De_ESCorr[2] + t_FilterParam.KH1[3] * devangle[0];
            D0_ESCorr[0] = D0_ESCorr[0] + t_FilterParam.KH1[4] * devangle[0];
            D0_ESCorr[2] = D0_ESCorr[2] + t_FilterParam.KH1[5] * devangle[0];

            Atti_ESG[1] = Atti_ESG[1] + t_FilterParam.KH2[0] * devangle[1];
            pIp->csGyroData_De_ESCorr[1] = t_FilterParam.Kg[1] * pIp->csGyroData_De_ESCorr[1] + t_FilterParam.KH2[1] * devangle[1];
            D0_ESCorr[1] = D0_ESCorr[1] + t_FilterParam.KH2[2] * devangle[1];

            /* 陀螺漂移限幅 */
            for (i=0; i<3; i++)
            {
                D0_ESCorr[i] = LimitDouble(D0_ESCorr[i], Mlf_D0);
                pIp->csGyroData_De_ESCorr[i] = LimitDouble(pIp->csGyroData_De_ESCorr[i], Mlf_De);
            }
        }
    }

    return;
}
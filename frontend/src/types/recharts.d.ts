declare module 'recharts' {
  import { ComponentType, ReactNode } from 'react';

  export interface LineChartProps {
    data?: any[];
    width?: number;
    height?: number;
    margin?: { top?: number; right?: number; bottom?: number; left?: number };
    children?: ReactNode;
  }

  export interface LineProps {
    type?: 'basis' | 'basisClosed' | 'basisOpen' | 'linear' | 'linearClosed' | 'natural' | 'monotoneX' | 'monotoneY' | 'monotone' | 'step' | 'stepBefore' | 'stepAfter';
    dataKey: string;
    stroke?: string;
    strokeWidth?: number;
    dot?: boolean | object | ComponentType;
    activeDot?: boolean | object | ComponentType;
  }

  export interface XAxisProps {
    dataKey?: string;
    domain?: [number | string, number | string];
    tickFormatter?: (value: any) => string;
  }

  export interface YAxisProps {
    domain?: [number | string, number | string];
    tickFormatter?: (value: any) => string;
  }

  export interface CartesianGridProps {
    strokeDasharray?: string;
  }

  export interface LegendProps {
    verticalAlign?: 'top' | 'middle' | 'bottom';
    align?: 'left' | 'center' | 'right';
  }

  export interface TooltipProps {
    cursor?: boolean | object;
    content?: ComponentType<any>;
  }

  export interface ResponsiveContainerProps {
    width?: number | string;
    height?: number | string;
    aspect?: number;
    children?: ReactNode;
  }

  export const LineChart: ComponentType<LineChartProps>;
  export const Line: ComponentType<LineProps>;
  export const XAxis: ComponentType<XAxisProps>;
  export const YAxis: ComponentType<YAxisProps>;
  export const CartesianGrid: ComponentType<CartesianGridProps>;
  export const Legend: ComponentType<LegendProps>;
  export const Tooltip: ComponentType<TooltipProps>;
  export const ResponsiveContainer: ComponentType<ResponsiveContainerProps>;
}

import { render } from '@testing-library/react'
import TimeseriesChart from '../components/TimeseriesChart'

test('renders chart container', () => {
  render(<TimeseriesChart data={[{fy:2020, revenue:100, eps:5}]} lines={[{dataKey:'revenue', name:'Revenue'}]} />)
})
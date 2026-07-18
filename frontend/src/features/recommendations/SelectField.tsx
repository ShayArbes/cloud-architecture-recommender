import { humanize } from '../../constants/enums';

interface SelectFieldProps<T extends string> {
  label: string;
  value: T | '';
  options: readonly T[];
  onChange: (value: T) => void;
}

/** A single labelled enum select whose options come from the shared constants. */
export function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
}: SelectFieldProps<T>) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <select
        value={value}
        onChange={(event) => {
          onChange(event.target.value as T);
        }}
        required
      >
        <option value="" disabled>
          Select…
        </option>
        {options.map((option) => (
          <option key={option} value={option}>
            {humanize(option)}
          </option>
        ))}
      </select>
    </label>
  );
}
